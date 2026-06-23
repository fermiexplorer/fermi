"""Propulsion, power, and mass models for the candidate architectures.

The central trade is *where the energy comes from*. Electric propulsion needs
electrical energy ~ (1/2) m_prop v_e^2 / eta. That energy can be supplied by:

* the Sun (solar arrays)  -- free, but falls off as 1/r^2;
* chemical reactants (fuel cells) -- carried mass, ~MJ/kg;
* a radioisotope/reactor -- carried mass, but ~GJ/kg (not modelled in detail).

For a fixed delta-v, electrical energy scales with v_e, so raising Isp *saves
propellant but costs energy*. With free solar energy you want high Isp; with an
energy-limited source (fuel cell) high Isp is catastrophic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import constants as c


def exhaust_velocity(isp_s: float) -> float:
    return isp_s * c.G0


def propellant_mass(dry_mass: float, dv: float, isp_s: float) -> float:
    """Tsiolkovsky propellant mass for a given dry (final) mass."""
    return dry_mass * (math.exp(dv / exhaust_velocity(isp_s)) - 1.0)


def minimal_dry_mass(
    active_kg: float, payload_kg: float, dv: float, isp_s: float,
    tank_frac: float, struct_frac: float,
):
    """Self-consistent MINIMAL dry mass — no extraneous bus margin.

    The dry (final) mass is built up from only what must be there:
        dry = active + tank + structure          (+ payload, in dry_eff)
    where ``active`` = power source + thruster/PPU (propellant-independent),
        tank      = tank_frac · m_prop,
        structure = struct_frac · (active + tank + m_prop)   (frame/harness/mounts),
        m_prop    = dry_eff · (MR − 1),  dry_eff = dry + payload.

    Substituting m_prop = dry_eff·K (K = MR−1) gives a closed form. The denominator
    D = 1 − K·(ft + ks·(ft+1)) is the convergence condition: if D ≤ 0 the
    propellant + tank + structure mass spirals without bound (the rocket-equation
    wall) and the design does NOT close. Returns ``None`` in that case.
    """
    K = math.exp(dv / exhaust_velocity(isp_s)) - 1.0
    ft, ks = tank_frac, struct_frac
    D = 1.0 - K * (ft + ks * (ft + 1.0))
    if D <= 0.0:
        return None
    dry_eff = (active_kg * (1.0 + ks) + payload_kg) / D
    m_prop = dry_eff * K
    tank = ft * m_prop
    structure = ks * (active_kg + tank + m_prop)
    dry_bus = active_kg + tank + structure
    return {
        "dry_eff": dry_eff, "dry_bus": dry_bus, "m_prop": m_prop,
        "tank": tank, "structure": structure, "wet": dry_eff + m_prop,
    }


def electrical_energy(prop_mass: float, isp_s: float, eta: float) -> float:
    """Electrical energy to expel ``prop_mass`` at the given Isp (J)."""
    ve = exhaust_velocity(isp_s)
    return 0.5 * prop_mass * ve**2 / eta


def thrust_from_power(power_w: float, isp_s: float, eta: float) -> float:
    """Thruster force for a given input electrical power (N)."""
    return 2.0 * eta * power_w / exhaust_velocity(isp_s)


def thrust_phase_duration(prop_mass: float, isp_s: float, power_w: float, eta: float) -> float:
    """Time to expel the propellant at constant power (s)."""
    ve = exhaust_velocity(isp_s)
    thrust = thrust_from_power(power_w, isp_s, eta)
    total_impulse = prop_mass * ve
    return total_impulse / thrust


# --- Reactant specific energies (electrical, after fuel-cell efficiency loss) ---
# Useful chemical energy content per kg of *total* reactant (fuel + oxidiser).
SPECIFIC_ENERGY = {
    "H2/O2": 8.0e6,        # J/kg of mixture (LHV-limited, ~2.2 kWh/kg)
    "hydrazine": 1.6e6,    # J/kg (monoprop decomposition)
    "RTG_Pu238": 2.2e12,   # J/kg (for contrast: radioisotope, ~5e5 x chemical)
}


SOLAR_CONST_1AU = 1361.0  # W/m^2, solar irradiance at 1 AU


def solar_array_area(power_w: float, cell_efficiency: float, distance_au: float = 1.0) -> float:
    """Deployed array area (m^2) to generate ``power_w`` electrical at ``distance_au``.

    Available electrical flux = (solar constant / r^2) * end-to-end efficiency.
    """
    flux = SOLAR_CONST_1AU / distance_au**2
    return power_w / (flux * cell_efficiency)


@dataclass
class SolarArchitecture:
    """Solar-electric vehicle with a sized array and a sized propulsion subsystem.

    Defaults are *commercial, available-today* hardware (no exotic techniques):
    ~20% monocrystalline SILICON cells (mass-produced, as on Starlink-class
    satellites -- not GaAs), a conventional lightweight flat array at ~3 kg/m^2
    (~90 W/kg at 1 AU BOL), a ~6 kg/kW off-the-shelf Hall-thruster + PPU, and an
    ~8% xenon COPV tank fraction. Silicon trades efficiency for cost: the array is
    larger and a bit heavier than a GaAs one, but cheap and proven. ``dry_mass`` is
    the total dry (final) mass used in the rocket equation; ``summary`` decomposes
    it so you can see whether the array + engine + tank fit inside it, leaving the
    remainder for bus + payload + margin.
    """

    dry_mass: float
    dv: float
    isp_s: float
    eta: float = 0.6
    array_power_1au_w: float = 5000.0
    cell_efficiency: float = 0.20          # commercial monocrystalline silicon, end-to-end
    areal_density_kg_m2: float = 3.0       # lightweight flat silicon array (~90 W/kg)
    engine_specific_mass_kg_kw: float = 6.0  # off-the-shelf Hall thruster + PPU
    tank_fraction: float = 0.08            # xenon COPV tankage as fraction of propellant
    distance_au: float = 1.0               # heliocentric distance the array is sized at

    def array_area_m2(self) -> float:
        return solar_array_area(self.array_power_1au_w, self.cell_efficiency, self.distance_au)

    def summary(self) -> dict:
        m_prop = propellant_mass(self.dry_mass, self.dv, self.isp_s)
        E = electrical_energy(m_prop, self.isp_s, self.eta)
        area = self.array_area_m2()
        array_mass = area * self.areal_density_kg_m2
        specific_power = self.array_power_1au_w / array_mass
        engine_mass = self.engine_specific_mass_kg_kw * self.array_power_1au_w / 1000.0
        tank_mass = self.tank_fraction * m_prop
        subsystems = array_mass + engine_mass + tank_mass
        thrust = thrust_from_power(self.array_power_1au_w, self.isp_s, self.eta)
        t_burn = thrust_phase_duration(m_prop, self.isp_s, self.array_power_1au_w, self.eta)
        return {
            "prop_mass_kg": m_prop,
            "energy_kWh": E / 3.6e6,
            "array_area_m2": area,
            "array_mass_kg": array_mass,
            "array_specific_power_w_per_kg": specific_power,
            "engine_ppu_mass_kg": engine_mass,
            "tank_mass_kg": tank_mass,
            "subsystems_kg": subsystems,  # array + engine + tank
            "bus_payload_remainder_kg": self.dry_mass - subsystems,
            "thrust_mN": thrust * 1e3,
            "burn_years": t_burn / c.YEAR,
            "wet_mass_kg": self.dry_mass + m_prop,
        }


@dataclass
class FuelCellArchitecture:
    """Energy-limited: reactants supply the electrical energy for the ion engine.

    Two reactant pools are modelled: propellant (xenon, expelled by the thruster)
    and fuel-cell reactant (burned only for watt-hours). They can be the *same*
    mass if the spent reactant is used as propellant, but then v_e is capped by
    the chemical energy. We model the general (separate) case and report both.
    """

    dry_mass: float
    dv: float
    isp_s: float
    eta_thruster: float = 0.6
    eta_fuelcell: float = 0.6
    reactant: str = "H2/O2"

    def summary(self) -> dict:
        m_prop = propellant_mass(self.dry_mass, self.dv, self.isp_s)
        E = electrical_energy(m_prop, self.isp_s, self.eta_thruster)
        e_chem = SPECIFIC_ENERGY[self.reactant] * self.eta_fuelcell
        reactant_mass = E / e_chem
        return {
            "prop_mass_kg": m_prop,
            "energy_kWh": E / 3.6e6,
            "reactant_mass_kg": reactant_mass,
            "consumables_kg": m_prop + reactant_mass,
            "wet_mass_kg": self.dry_mass + m_prop + reactant_mass,
        }


def _golden_min(f, lo: float, hi: float, tol: float = 1e-3):
    """Minimise a unimodal f on [lo, hi] by golden-section search."""
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c1 = b - gr * (b - a)
    c2 = a + gr * (b - a)
    f1, f2 = f(c1), f(c2)
    while b - a > tol:
        if f1 < f2:
            b, c2, f2 = c2, c1, f1
            c1 = b - gr * (b - a)
            f1 = f(c1)
        else:
            a, c1, f1 = c1, c2, f2
            c2 = a + gr * (b - a)
            f2 = f(c2)
    return 0.5 * (a + b)


def fuelcell_optimum_isp(
    reactant: str, eta_thruster: float, eta_fuelcell: float, dv: float
) -> float:
    """Isp that minimises (propellant + reactant) mass for a fuel-cell EP system.

    There is no clean closed form: propellant mass is exponential in dv/v_e while
    reactant mass grows as v_e^2, so the optimum is found numerically. (The naive
    closed form v_e* = sqrt(2*eta*e_chem) only holds in the v_e >> dv limit, which
    does NOT apply here -- the optimum lands near v_e ~ dv, low-Isp territory.)
    """
    e_chem = SPECIFIC_ENERGY[reactant] * eta_fuelcell

    def consumables_per_dry(isp: float) -> float:
        ve = isp * c.G0
        m_prop = math.exp(dv / ve) - 1.0
        m_react = 0.5 * m_prop * ve**2 / (eta_thruster * e_chem)
        return m_prop + m_react

    return _golden_min(consumables_per_dry, 200.0, 4000.0)


def max_ve_self_powered(reactant: str, eta_thruster: float, eta_fuelcell: float) -> float:
    """If the propellant IS the reactant (spent exhaust expelled), the energy
    released accelerating 1 kg caps its own exhaust velocity at sqrt(2*eta*e_chem).
    """
    e_chem = SPECIFIC_ENERGY[reactant] * eta_fuelcell
    return math.sqrt(2.0 * eta_thruster * e_chem)
