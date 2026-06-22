"""Alpha Centauri ion-propulsion mission -- integrated feasibility analysis.

Run:  .venv/bin/python run_analysis.py
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

from fermi_sim import constants as c
from fermi_sim.astro import alpha_centauri_state
from fermi_sim.departure import (
    departure_budget,
    impulsive_dv_from_leo,
    v_inf_earth_required,
)
from fermi_sim.intercept import (
    ecliptic_crossing_time,
    min_speed_arrival,
    solve_intercept,
)
from fermi_sim.spacecraft import (
    FuelCellArchitecture,
    SolarArchitecture,
    exhaust_velocity,
    fuelcell_optimum_isp,
    max_ve_self_powered,
    propellant_mass,
)
from fermi_sim.trajectory import (
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
    """Arrival time minimising departure delta-v in a regime."""

    def objective(t_yr: float) -> float:
        sol = solve_intercept(state, t_yr * c.YEAR)
        v_inf_e, _ = v_inf_earth_required(sol.v_inf, sol.plane_angle_deg)
        if regime == "impulsive":
            return impulsive_dv_from_leo(v_inf_e, 400.0)
        if regime == "lowthrust":
            return v_inf_e
        raise ValueError(f"unknown departure regime: {regime}")

    res = minimize_scalar(objective, bounds=(lo_yr, hi_yr), method="bounded", options={"xatol": 1.0})
    t_yr = float(res.x)
    sol = solve_intercept(state, t_yr * c.YEAR)
    dep = departure_budget(sol.v_inf, sol.plane_angle_deg)
    dv = dep.dv_impulsive if regime == "impulsive" else dep.dv_low_thrust
    return t_yr, dv, sol, dep


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
        arch = SolarArchitecture(dry_mass=255.0, dv=dv_design, isp_s=isp)
        s = arch.summary()
        print(
            f"Isp {isp:>4}s: xenon {s['prop_mass_kg']:5.0f} kg "
            f"(frac {s['prop_mass_kg'] / s['wet_mass_kg']:.2f}), wet "
            f"{s['wet_mass_kg']:5.0f} kg, thrust {s['thrust_mN']:4.0f} mN, "
            f"burn {s['burn_years']:.1f} yr, energy {s['energy_kWh']:,.0f} kWh"
        )
    print("\nCommercial silicon subsystem sizing @ 5 kW, 1 AU (20% Si cells, 3 kg/m^2,")
    print("6 kg/kW thruster+PPU, 8% xenon tank -- Starlink-class, buy-today), Isp 3000 s:")
    s = SolarArchitecture(dry_mass=255.0, dv=dv_design, isp_s=3000).summary()
    print(
        f"  solar array : {s['array_area_m2']:5.1f} m^2, {s['array_mass_kg']:4.0f} kg "
        f"({s['array_specific_power_w_per_kg']:.0f} W/kg)"
    )
    print(f"  thruster+PPU: {s['engine_ppu_mass_kg']:4.0f} kg")
    print(f"  xenon tank  : {s['tank_mass_kg']:4.0f} kg  (+ {s['prop_mass_kg']:.0f} kg xenon)")
    print(
        f"  -> array+engine+tank = {s['subsystems_kg']:.0f} kg of the {255:.0f} kg dry mass;"
        f" {s['bus_payload_remainder_kg']:.0f} kg left for bus + payload + margin."
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
    array_kg = SolarArchitecture(dry_mass=dry, dv=dv_design, isp_s=3000).summary()["array_mass_kg"]
    print(
        f"\nMass-optimal fuel-cell Isp: {isp_opt:.0f} s "
        f"(v_e {exhaust_velocity(isp_opt) / KMS:.1f} km/s) -> still "
        f"{fc_opt['consumables_kg']:,.0f} kg of consumables "
        f"(vs ~{array_kg:.0f} kg of silicon solar array)."
    )
    print(
        f"If spent reactant IS the propellant, v_e is capped at "
        f"{ve_self / KMS:.1f} km/s (Isp {ve_self / c.G0:.0f} s) -- chemical-rocket class."
    )
    print("=> Chemical energy (~MJ/kg) is 10^4-10^5x too sparse to feed an ion engine.")
    print("   Deep-space EP power must be solar (near the Sun -- but it saturates far out, see")
    print("   sec 7) or a nuclear-electric reactor -- not fuel cells, and not a low-power RTG.")

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
    header("7. CONSERVATIVE FEASIBILITY -- THE 1/r^2 POWER GATE (decisive)")
    from fermi_sim.departure import sep_achievable_vinf

    floor = 23.4e3
    dry_pay = 256.0
    dv_cons = 30_000.0  # conservative pure-EP departure (heliocentric spiral, no Earth-velocity borrow)
    print("Sections 2-3 size the OPTIMISTIC baseline. The decisive conservative test: as the probe")
    print("spirals out, SOLAR power falls as 1/r^2, thrust starves, and the achievable cruise v_inf")
    print(f"SATURATES. A pure-electric departure closes only if it reaches the {floor / KMS:.1f} km/s floor.\n")
    ve = exhaust_velocity(3000)
    wet = dry_pay * np.exp(dv_cons / ve)  # ~30 km/s conservative departure at gridded-ion Isp
    print(f"Gridded ion (Isp 3000 s), conservative ~{dv_cons / KMS:.0f} km/s departure "
          f"(wet {wet:.0f} kg / dry {dry_pay:.0f} kg):")
    for kw in (5, 10, 20):
        vs = sep_achievable_vinf(kw * 1e3, wet, dry_pay, 3000, 0.5, 1.0, 2.0)  # SOLAR 1/r^2 fade
        tag = "closes" if vs >= floor else "SATURATES < floor -> NOT feasible"
        print(f"   SOLAR  (1/r^2)   {kw:2d} kW -> v_inf {vs / KMS:5.1f} km/s   {tag}")
    for kw in (1, 3, 5):
        vn = sep_achievable_vinf(kw * 1e3, wet, dry_pay, 3000, 0.55, 1.0, 0.0)  # NUCLEAR constant power
        tag = "CLOSES (constant power, no fade)" if vn >= floor else "short -- raise reactor power"
        print(f"   NUCLEAR (const) {kw:2d} kW -> v_inf {vn / KMS:5.1f} km/s   {tag}")
    print(
        "\n=> Pure SOLAR-electric is POWER-LIMITED and does NOT close from LEO (any power: bigger\n"
        "   array -> more mass, same saturation). The pure-electric path that DOES close is\n"
        "   NUCLEAR-ELECTRIC (constant power): ~5 kW fission reactor @ ~40 W/kg + gridded ion\n"
        "   (Isp ~3000 s) -> v_inf ~24.8 km/s, ~64% xenon, ~+64 kg dry-bus margin. An RTG is the\n"
        "   right kind of power but too low (<=1 kW -> only ~15-18 km/s) and too heavy (~5 W/kg)."
    )

    # ---------------------------------------------------------------
    header("8. VERDICT (conservative)")
    print(
        "* The mission CLOSES, but only the conservative power gate settles it. PURE SOLAR-\n"
        "  ELECTRIC from LEO is power-limited (1/r^2 fade) and does NOT reach the 23.4 km/s\n"
        "  cruise floor at practical masses -- the optimistic ~20 km/s baseline (sec 2-3) is\n"
        "  necessary but not sufficient.\n"
        "* Three architectures DO close:\n"
        "    - NUCLEAR-ELECTRIC ion (constant power): the only PURE-ELECTRIC path; ~5 kW reactor\n"
        "      @ ~40 W/kg + gridded ion -> ~24.8 km/s, mass closes. Carries a reactor.\n"
        "    - SOLAR-OBERTH: a ~1.4 km/s burn at ~10 Rsun yields the full 24 km/s (~4.3x Oberth\n"
        "      leverage), but the burn must be CHEMICAL (ion too slow for the hours-long pass),\n"
        "      needs a Parker-class heat shield (~1830 K), and a Jupiter/Venus tour to drop\n"
        "      perihelion. Sidesteps the power wall rather than solving it.\n"
        "    - CHEMICAL kick: ~14 km/s impulsive from LEO does it all (a 3.7 km/s kick does NOT --\n"
        "      it barely escapes Earth; v_inf adds in quadrature, so a useful kick is ~10+ km/s).\n"
        "* Solar still beats fuel cells decisively (energy density); fuel cells remain a dead end.\n"
        "* Arrival ~73,000 yr (75,000 yr nearly identical), aimed close to the ecliptic."
    )


if __name__ == "__main__":
    main()
