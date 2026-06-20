"""Alpha Centauri ion-propulsion mission -- integrated feasibility analysis.

Run:  .venv/bin/python run_analysis.py
"""

from __future__ import annotations

import numpy as np

from acsim import constants as c
from acsim.astro import alpha_centauri_state
from acsim.departure import departure_budget
from acsim.intercept import (
    ecliptic_crossing_time,
    min_speed_arrival,
    solve_intercept,
)
from acsim.spacecraft import (
    FuelCellArchitecture,
    SolarArchitecture,
    exhaust_velocity,
    fuelcell_optimum_isp,
    max_ve_self_powered,
    propellant_mass,
)
from acsim.trajectory import (
    jupiter_assist_max_gain,
    solar_oberth_burn_for_vinf,
    solar_oberth_vinf,
    time_to_ac,
)

KMS = c.KMS
LINE = "=" * 72


def header(title: str) -> None:
    print(f"\n{LINE}\n{title}\n{LINE}")


def find_min_dv_arrival(state, regime: str, lo_yr=50_000, hi_yr=100_000):
    """Brute-force the arrival time minimising departure delta-v in a regime."""
    best = None
    for t_yr in np.linspace(lo_yr, hi_yr, 120):
        sol = solve_intercept(state, t_yr * c.YEAR)
        dep = departure_budget(sol.v_inf, sol.plane_angle_deg)
        dv = dep.dv_impulsive if regime == "impulsive" else dep.dv_low_thrust
        if best is None or dv < best[1]:
            best = (t_yr, dv, sol, dep)
    return best


def main() -> None:
    state = alpha_centauri_state()

    # ---------------------------------------------------------------
    header("1. INTERCEPT GEOMETRY")
    dist = np.linalg.norm(state.r)
    print(f"Alpha Centauri now:  {dist / c.LY:.3f} ly = {dist / c.AU:,.0f} AU")
    print(f"Space velocity:      {np.linalg.norm(state.v) / KMS:.2f} km/s")
    print(f"Target miss distance for 'arrival': 2600 AU (~1% = 99% of the way)")
    tan = min_speed_arrival(state)
    t_ecl = ecliptic_crossing_time(state) / c.YEAR
    print(
        f"\nTangential (min-SPEED) intercept: {tan.arrival_time_yr:>8,.0f} yr"
        f"  ->  v_inf = {tan.v_inf / KMS:.2f} km/s, tilt {tan.plane_angle_deg:+.1f} deg"
    )
    print(f"AC track crosses the ecliptic at: {t_ecl:>8,.0f} yr  (in-plane departure)")

    # ---------------------------------------------------------------
    header("2. MINIMUM DEPARTURE DELTA-V FROM LEO (DIRECT, NO GRAVITY ASSIST)")
    print("Departure delta-v vs arrival time (LEO 400 km):\n")
    print(f"{'T (yr)':>9} {'v_inf_sun':>10} {'tilt':>7} {'dv_impulsive':>13} {'dv_lowthrust':>13}")
    for t_yr in [58_000, 65_000, 75_000, 80_000, 90_000, 100_000]:
        sol = solve_intercept(state, t_yr * c.YEAR)
        dep = departure_budget(sol.v_inf, sol.plane_angle_deg)
        print(
            f"{t_yr:>9,} {sol.v_inf / KMS:>10.2f} {sol.plane_angle_deg:>+7.1f}"
            f" {dep.dv_impulsive / KMS:>11.2f}  {dep.dv_low_thrust / KMS:>11.2f}"
        )

    t_imp, dv_imp, sol_imp, dep_imp = find_min_dv_arrival(state, "impulsive")
    t_lt, dv_lt, sol_lt, dep_lt = find_min_dv_arrival(state, "lowthrust")
    print(
        f"\nMIN impulsive (chemical, full Oberth): {dv_imp / KMS:5.1f} km/s"
        f"  at {t_imp:,.0f} yr (tilt {sol_imp.plane_angle_deg:+.1f} deg)"
    )
    print(
        f"MIN naive continuous spiral (worst):   {dv_lt / KMS:5.1f} km/s"
        f"  at {t_lt:,.0f} yr"
    )
    print("Optimised perigee-biased SEP (industry benchmark): ~20 km/s")
    print("=> The true low-thrust budget lies between the floor and the spiral bound.")

    # ---------------------------------------------------------------
    header("3. BASELINE: ION + SOLAR, 500 kg CLASS, 20 km/s")
    dv_design = 20_000.0
    for isp in [2000, 3000, 4000]:
        for dry in [255.0]:
            arch = SolarArchitecture(dry_mass=dry, dv=dv_design, isp_s=isp)
            s = arch.summary()
            print(
                f"Isp {isp:>4}s: prop {s['prop_mass_kg']:5.0f} kg "
                f"(frac {s['prop_mass_kg'] / s['wet_mass_kg']:.2f}), wet "
                f"{s['wet_mass_kg']:5.0f} kg, array {s['array_mass_kg']:4.0f} kg @5kW, "
                f"thrust {s['thrust_mN']:5.0f} mN, burn {s['burn_years']:.1f} yr, "
                f"energy {s['energy_kWh']:,.0f} kWh"
            )
    print("\nPropellant fraction ~0.4-0.5 xenon is comfortably feasible today.")

    # ---------------------------------------------------------------
    header("4. THE FUEL-CELL ENERGY WALL (why solar wins)")
    dry = 255.0
    print(f"Electrical energy for 20 km/s on a {dry:.0f} kg dry craft, vs Isp:")
    print(f"{'Isp (s)':>8} {'v_e km/s':>9} {'prop kg':>9} {'energy kWh':>11}"
          f" {'H2/O2 reactant kg':>18}")
    for isp in [300, 1000, 3000, 5000, 50000]:
        fc = FuelCellArchitecture(dry_mass=dry, dv=dv_design, isp_s=isp)
        s = fc.summary()
        print(
            f"{isp:>8,} {exhaust_velocity(isp) / KMS:>9.1f} {s['prop_mass_kg']:>9.1f}"
            f" {s['energy_kWh']:>11,.0f} {s['reactant_mass_kg']:>18,.0f}"
        )
    isp_opt = fuelcell_optimum_isp("H2/O2", 0.6, 0.6, dv_design)
    ve_self = max_ve_self_powered("H2/O2", 0.6, 0.6)
    fc_opt = FuelCellArchitecture(dry_mass=dry, dv=dv_design, isp_s=isp_opt).summary()
    print(
        f"\nMass-optimal fuel-cell Isp: {isp_opt:.0f} s "
        f"(v_e {exhaust_velocity(isp_opt) / KMS:.1f} km/s) -> still "
        f"{fc_opt['consumables_kg']:,.0f} kg of consumables (vs ~33 kg of solar array)."
    )
    print(
        f"If spent reactant IS the propellant, v_e is capped at "
        f"{ve_self / KMS:.1f} km/s (Isp {ve_self / c.G0:.0f} s) -- chemical-rocket class."
    )
    print("=> Chemical energy (~MJ/kg) is 10^4-10^5x too sparse to feed an ion engine.")
    print("   Deep-space EP power must be solar (near Sun) or nuclear/RTG -- not fuel cells.")

    # ---------------------------------------------------------------
    header("5. TIME TO AC vs CRUISE SPEED (architecture comparison)")
    print("Transit time depends on cruise v_inf, NOT on how you got it:")
    print(f"{'v_inf km/s':>11} {'arrival (yr)':>14}  note")
    notes = {
        19: "near floor; misses tighter aims",
        24: "ion+solar / chemical+GA baseline (min-dv)",
        30: "aggressive SEP or solar Oberth",
        50: "solar Oberth w/ heat shield",
        100: "advanced (nuclear-EP / large Oberth)",
    }
    for v in [19, 24, 30, 50, 100]:
        t = time_to_ac(state, v * KMS)
        ts = f"{t / c.YEAR:,.0f}" if t else "no intercept"
        print(f"{v:>11} {ts:>14}  {notes[v]}")

    # ---------------------------------------------------------------
    header("6. DIRECT vs GRAVITY-ASSIST ('hops')")
    print("Need heliocentric v_inf ~ 24 km/s. Voyager-1 left at ~16.6 km/s.\n")
    gain = jupiter_assist_max_gain(9_000.0)  # ~9 km/s approach rel. to Jupiter
    print(
        f"Jupiter flyby: up to ~{gain / KMS:.1f} km/s heliocentric gain (best geometry)."
        f"\n  -> can supply much of the 24 km/s, BUT needs Jupiter in the AC aim"
        f"\n     direction + ~6 yr cruise to Jupiter. Often not aligned; the direct"
        f"\n     concept deliberately skips it for schedule/simplicity."
    )
    print("\nSolar Oberth (powered close perihelion):")
    print(f"{'perihelion':>12} {'burn dv for v_inf=24':>22} {'v_inf @ 2 km/s burn':>22}")
    for rp in [4, 6, 10, 20]:
        burn = solar_oberth_burn_for_vinf(rp, 24_000.0)
        vinf2 = solar_oberth_vinf(rp, 2_000.0)
        print(f"{rp:>9} Rsun {burn / KMS:>20.2f} {vinf2 / KMS:>20.2f}")
    print(
        "  -> A ~1-2 km/s burn near the Sun yields the whole 24 km/s (huge Oberth"
        "\n     leverage), but needs a heat shield + a way to drop perihelion"
        "\n     (retro burn or a Jupiter/Venus assist). Best for an absolute-min-dv,"
        "\n     cost-no-object variant; heavier & more complex than direct SEP."
    )

    # ---------------------------------------------------------------
    header("7. VERDICT")
    print(
        "* Direct LEO->AC with solar-electric ion is FEASIBLE: ~20 km/s low-thrust\n"
        "  budget, ~40-50% xenon, ~75-80k yr arrival, well inside 100k yr.\n"
        "* Minimum direct departure delta-v from LEO: ~14 km/s (impulsive floor),\n"
        "  ~20 km/s realistic SEP, arriving ~75,000 yr, aimed ~1.5 deg off ecliptic\n"
        "  near AC's ecliptic crossing -- matching your intuition.\n"
        "* Solar beats fuel cells decisively (energy density). Hybrid adds no value;\n"
        "  fuel-cell exhaust as propellant does not help -- energy, not v_e, is the wall.\n"
        "* Gravity assists are optional: a solar Oberth could cut onboard delta-v to a\n"
        "  few km/s but adds a heat shield; Jupiter rarely aligns. Direct is simplest."
    )


if __name__ == "__main__":
    main()
