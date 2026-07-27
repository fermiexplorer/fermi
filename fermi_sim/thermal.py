"""First-principles perihelion-array thermal derating (issue #5, roadmap Stage 7).

Replaces the ASSUMED perihelion power cap (``P(r) = P1*min((1 AU/r)^2, 4)``)
with a DERIVED curve from the array's own energy balance. Model: a flat panel,
sun-normal, radiating from both faces, with the extracted electricity removed
from the heat load (self-consistent, since the cell efficiency itself falls
with temperature):

    (alpha_s - eta(T)) * S(r) = (eps_front + eps_back) * sigma * T^4
    eta(T) = eta_ref * (1 - beta * (T - T_ref)),  floored at 0
    S(r)   = S0 / r^2   (r in AU)

    cap_eff(r) = (1/r^2) * eta(T(r)) / eta(T(1 AU))

so cap_eff is the effective power multiple relative to the array's own 1 AU
output — the exact quantity the pumping integrators multiply into thrust. The
temperature solve is a fixed-point iteration T <- [(alpha_s - eta(T))*S /
(eps*sigma)]^(1/4), run a FIXED number of times so the web mirror reproduces
it bit-for-bit; the integrators consume a precomputed log-radius table (same
grid + same linear interpolation in both languages) for speed and parity.

Cell/thermo-optical numbers are representative published values for rigid GaAs
panels with coverglass (absorptivity ~0.92, hemispherical emissivity ~0.85 per
face, temperature coefficient ~0.2 %/K; silicon ~0.45 %/K as the sensitivity
case). The old constant-cap form stays available in the integrators
(power_model="cap") as the independent audit comparator and the PSI-comparable
working point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SOLAR_CONST_1AU = 1361.0     # W/m^2 at 1 AU (same value the sizing model uses)
SIGMA_SB = 5.670374419e-8    # Stefan-Boltzmann, W m^-2 K^-4
_T_ITERS = 40                # fixed-point iterations (mirrored exactly in JS)

# Table grid for the integrators: log-spaced in r over the span trajectories
# actually visit (the pumping floor is 0.42 AU; cruise checks go out past 20 AU).
TABLE_R_MIN = 0.05
TABLE_R_MAX = 40.0
TABLE_N = 1024


@dataclass(frozen=True)
class ArrayThermal:
    """Thermo-optical + cell parameters of one array design."""
    alpha_s: float = 0.92     # solar absorptivity (cell + coverglass)
    eps_front: float = 0.85   # hemispherical emissivity, sun face
    eps_back: float = 0.85    # hemispherical emissivity, rear face
    eta_ref: float = 0.30     # cell efficiency at t_ref
    beta: float = 0.002       # fractional efficiency loss per K (GaAs ~0.2 %/K)
    t_ref: float = 301.15     # 28 C cell reference temperature

    def validate(self) -> None:
        if not (0.0 < self.alpha_s <= 1.0 and 0.0 < self.eps_front <= 1.0
                and 0.0 <= self.eps_back <= 1.0):
            raise ValueError(f"ArrayThermal: absorptivity/emissivities must be in (0,1], got {self}")
        if not (0.0 < self.eta_ref < self.alpha_s):
            raise ValueError(f"ArrayThermal: eta_ref must be in (0, alpha_s), got {self}")
        if not (0.0 <= self.beta < 0.02 and 150.0 < self.t_ref < 400.0):
            raise ValueError(f"ArrayThermal: beta/t_ref out of physical range, got {self}")


GAAS = ArrayThermal()                          # the shipped default
SI = ArrayThermal(eta_ref=0.20, beta=0.0045)   # silicon sensitivity case


def cell_temperature(r_au: float, m: ArrayThermal = GAAS) -> float:
    """Equilibrium cell temperature (K) at r (AU), electricity extraction included.

    Fixed-point iteration on T <- [(alpha_s - eta(T)) S / (eps sigma)]^(1/4);
    the map is a contraction here (|d eta/dT| * S << 4 eps sigma T^3 over the
    physical range) and _T_ITERS passes take it to double precision.
    """
    if not (math.isfinite(r_au) and r_au > 0.0):
        raise ValueError(f"cell_temperature: r_au must be positive and finite, got {r_au!r}")
    s = SOLAR_CONST_1AU / (r_au * r_au)
    eps = m.eps_front + m.eps_back
    t = 300.0
    for _ in range(_T_ITERS):
        eta = max(0.0, m.eta_ref * (1.0 - m.beta * (t - m.t_ref)))
        t = ((m.alpha_s - eta) * s / (eps * SIGMA_SB)) ** 0.25
    return t


def cell_efficiency(t_k: float, m: ArrayThermal = GAAS) -> float:
    """Linear temperature derating, floored at zero."""
    return max(0.0, m.eta_ref * (1.0 - m.beta * (t_k - m.t_ref)))


def cap_eff(r_au: float, m: ArrayThermal = GAAS) -> float:
    """Effective power multiple vs the array's own 1 AU output (the DERIVED cap).

    cap_eff(1) == 1 by construction; below 1 AU it grows slower than 1/r^2
    because the cells heat and derate, peaks, and collapses to 0 where the
    equilibrium temperature reaches the eta = 0 point.
    """
    m.validate()
    eta_1 = cell_efficiency(cell_temperature(1.0, m), m)
    eta_r = cell_efficiency(cell_temperature(r_au, m), m)
    return (1.0 / (r_au * r_au)) * (eta_r / eta_1)


def cap_eff_table(m: ArrayThermal = GAAS):
    """(r_grid, cap_grid) on the fixed log grid — what the integrators interpolate.

    The identical grid + linear interpolation is mirrored in web/physics.js so
    the two engines stay in parity to machine precision.
    """
    m.validate()
    lo, hi = math.log(TABLE_R_MIN), math.log(TABLE_R_MAX)
    rs, caps = [], []
    for i in range(TABLE_N):
        r = math.exp(lo + (hi - lo) * i / (TABLE_N - 1))
        rs.append(r)
        caps.append(cap_eff(r, m))
    return rs, caps


def cap_eff_interp(m: ArrayThermal = GAAS):
    """A fast cap(r_au) callable: linear interpolation on the fixed log grid,
    clamped to the table ends (below 0.05 AU the model has already collapsed
    to ~0; above 40 AU the factor is ~0 anyway)."""
    rs, caps = cap_eff_table(m)
    lo, hi = math.log(TABLE_R_MIN), math.log(TABLE_R_MAX)
    scale = (TABLE_N - 1) / (hi - lo)

    def cap(r_au: float) -> float:
        x = (math.log(min(max(r_au, TABLE_R_MIN), TABLE_R_MAX)) - lo) * scale
        i = min(int(x), TABLE_N - 2)
        f = x - i
        return caps[i] + f * (caps[i + 1] - caps[i])

    return cap
