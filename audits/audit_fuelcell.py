"""Audit 5 -- the fuel-cell energy wall.

Independent checks:
* Reactant mass recomputed from first principles (energy / specific energy).
* The mass-optimal fuel-cell EP Isp found by golden-section search matches an
  independent scipy minimisation.
* The self-powered exhaust-velocity cap.
* Order-of-magnitude: a fuel cell needs >=1000x the mass of a solar array.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize_scalar

from _util import check, rel_err, summary

from fermi_sim import constants as c
from fermi_sim.spacecraft import (
    SPECIFIC_ENERGY,
    FuelCellArchitecture,
    electrical_energy,
    exhaust_velocity,
    fuelcell_optimum_isp,
    max_ve_self_powered,
    propellant_mass,
)


def run() -> None:
    print("== Audit 5: fuel-cell energy wall ==")

    dry, dv, eta_t, eta_fc = 255.0, 20e3, 0.6, 0.6
    e_chem = SPECIFIC_ENERGY["H2/O2"]

    # 1. Reactant mass from first principles at Isp 3000 s.
    isp = 3000.0
    mp = propellant_mass(dry, dv, isp)
    E = electrical_energy(mp, isp, eta_t)
    reactant_indep = E / (eta_fc * e_chem)
    fc = FuelCellArchitecture(dry_mass=dry, dv=dv, isp_s=isp).summary()
    check("reactant mass matches first-principles energy/e_chem",
          rel_err(reactant_indep, fc["reactant_mass_kg"]) < 1e-9,
          f"{reactant_indep:,.0f} kg")

    # 2. Mass-optimal Isp: engine golden-section search vs independent scipy.
    def total_consumables(isp):
        s = FuelCellArchitecture(dry_mass=dry, dv=dv, isp_s=isp).summary()
        return s["consumables_kg"]

    res = minimize_scalar(total_consumables, bounds=(300, 4000), method="bounded")
    isp_engine = fuelcell_optimum_isp("H2/O2", eta_t, eta_fc, dv)
    check("mass-optimal Isp: engine (golden-section) matches scipy minimiser (<3%)",
          rel_err(isp_engine, res.x) < 0.03,
          f"engine {isp_engine:.0f} s vs scipy {res.x:.0f} s")
    check("mass-optimal fuel-cell Isp is low (v_e ~ dv, not high-Isp)",
          800 < isp_engine < 2000, f"{isp_engine:.0f} s")

    # 3. Self-powered exhaust-velocity cap = sqrt(2 eta e_chem).
    ve_cap = max_ve_self_powered("H2/O2", eta_t, eta_fc)
    check("self-powered v_e cap == sqrt(2 eta e_chem)",
          rel_err(ve_cap, math.sqrt(2 * eta_t * eta_fc * e_chem)) < 1e-12,
          f"{ve_cap/c.KMS:.2f} km/s (Isp {ve_cap/c.G0:.0f} s)")
    check("self-powered cap is chemical-rocket class (<5 km/s)", ve_cap < 5e3)

    # 4. Order-of-magnitude: fuel cell vs an equivalent 5 kW solar array (~33 kg).
    solar_array_kg = 5000.0 / 150.0
    ratio = fc["reactant_mass_kg"] / solar_array_kg
    check("fuel cell needs >=1000x the mass of a 5 kW solar array",
          ratio > 1000, f"{ratio:,.0f}x heavier")

    # 5. High Isp makes the fuel cell *worse* (energy scales with v_e).
    r3k = FuelCellArchitecture(dry_mass=dry, dv=dv, isp_s=3000).summary()["reactant_mass_kg"]
    r50k = FuelCellArchitecture(dry_mass=dry, dv=dv, isp_s=50000).summary()["reactant_mass_kg"]
    check("Isp 50,000 s needs more reactant than Isp 3000 s (energy wall)",
          r50k > r3k, f"{r3k:,.0f} -> {r50k:,.0f} kg")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
