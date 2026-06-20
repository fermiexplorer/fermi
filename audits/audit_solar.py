"""Audit 6 -- solar array sizing and propulsion subsystem masses.

Independent checks of the size/mass model: area from solar flux x efficiency,
mass from areal density, the 1/r^2 falloff, and the engine + tank masses.
"""

from __future__ import annotations

from _util import check, rel_err, summary

from fermi_sim import constants as c
from fermi_sim.spacecraft import (
    SOLAR_CONST_1AU,
    SolarArchitecture,
    propellant_mass,
    solar_array_area,
)


def run() -> None:
    print("== Audit 6: solar array & propulsion subsystem sizing ==")

    P, eff, areal = 5000.0, 0.20, 3.0
    arch = SolarArchitecture(
        dry_mass=255.0, dv=20e3, isp_s=3000,
        array_power_1au_w=P, cell_efficiency=eff, areal_density_kg_m2=areal,
        engine_specific_mass_kg_kw=6.0, tank_fraction=0.08,
    )
    s = arch.summary()

    # 1. Area = power / (flux * efficiency), flux = 1361 W/m^2 at 1 AU.
    area_indep = P / (SOLAR_CONST_1AU * eff)
    check("array area == P/(flux*eff)", rel_err(s["array_area_m2"], area_indep) < 1e-9,
          f"{s['array_area_m2']:.2f} m^2")

    # 2. Mass = area * areal density; specific power = P / mass.
    check("array mass == area * areal density",
          rel_err(s["array_mass_kg"], area_indep * areal) < 1e-9, f"{s['array_mass_kg']:.1f} kg")
    check("array specific power == flux*eff/areal",
          rel_err(s["array_specific_power_w_per_kg"], SOLAR_CONST_1AU * eff / areal) < 1e-9,
          f"{s['array_specific_power_w_per_kg']:.0f} W/kg")

    # 3. Commercial silicon lands in a believable band (~50-150 W/kg).
    check("silicon array specific power is realistic (50-150 W/kg)",
          50 < s["array_specific_power_w_per_kg"] < 150,
          f"{s['array_specific_power_w_per_kg']:.0f} W/kg")

    # 4. 1/r^2: same power needs 4x the area at 2 AU.
    a1 = solar_array_area(P, eff, 1.0)
    a2 = solar_array_area(P, eff, 2.0)
    check("area scales as r^2 (2 AU needs 4x)", rel_err(a2, 4 * a1) < 1e-9,
          f"{a1:.1f} -> {a2:.1f} m^2")

    # 5. Engine+PPU mass = specific mass * power(kW); tank = fraction * propellant.
    check("engine+PPU mass == 6 kg/kW * 5 kW", rel_err(s["engine_ppu_mass_kg"], 6.0 * 5.0) < 1e-9,
          f"{s['engine_ppu_mass_kg']:.0f} kg")
    mp = propellant_mass(255.0, 20e3, 3000)
    check("xenon tank == 8% of propellant", rel_err(s["tank_mass_kg"], 0.08 * mp) < 1e-9,
          f"{s['tank_mass_kg']:.1f} kg")

    # 6. Mass closes: array+engine+tank fit inside dry mass with room to spare.
    check("subsystems == array+engine+tank",
          rel_err(s["subsystems_kg"], s["array_mass_kg"] + s["engine_ppu_mass_kg"] + s["tank_mass_kg"]) < 1e-9)
    check("bus+payload remainder is positive (design closes)",
          s["bus_payload_remainder_kg"] > 0, f"{s['bus_payload_remainder_kg']:.0f} kg free")


if __name__ == "__main__":
    run()
    raise SystemExit(summary())
