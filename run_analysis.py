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
        "\n=> At CONSERVATIVE specific masses pure SOLAR-electric does NOT close. The binding variable\n"
        "   is the whole-vehicle specific power alpha = power/dry_mass, NOT the kilowatts. The pure-\n"
        "   electric path that closes at near-term specific masses is NUCLEAR-ELECTRIC (constant power):\n"
        "   ~5 kW reactor @ ~40 W/kg + gridded ion (Isp ~3000 s) -> v_inf ~24.8 km/s, ~64% xenon."
    )

    # ---------------------------------------------------------------
    header("7b. SOLAR FEASIBILITY FRONTIER -- the high-alpha corner (pure solar CAN close)")
    from fermi_sim.spacecraft import minimal_dry_mass
    floor2 = 24.0e3
    print("A light enough vehicle burns briefly NEAR 1 AU, so the 1/r^2 fade barely bites and the")
    print("achievable v_inf approaches the impulsive-from-1-AU limit (~38 km/s). Frontier vs alpha")
    print("(array W/kg + thruster kg/kW set alpha; Isp 2300, struct 9%, tank 4%, 2 kW, 1 kg payload):\n")
    print(f"{'array W/kg':>10} {'eng kg/kW':>9} {'alpha':>7} {'achV km/s':>10} {'result':>8}")
    for wkg, eng in ((100, 6), (300, 4), (300, 2), (600, 2), (800, 2)):
        active = 2000 / wkg + eng * 2.0
        r = minimal_dry_mass(active, 1.0, 30e3, 2300, 0.04, 0.09)
        achv = sep_achievable_vinf(2000, r["wet"], r["dry_eff"], 2300, 0.48, 1.0, 2.0)
        alpha = 2000 / r["dry_eff"]
        print(f"{wkg:>10} {eng:>9} {alpha:>7.0f} {achv / KMS:>10.1f} {'CLOSES' if achv >= floor2 else 'short':>8}")
    print(
        "\n=> Pure SOLAR-electric closes ABOVE alpha ~ 100 W/kg -- an ultralight ~50 kg micro-probe with\n"
        "   BOTH a light array (>=~300 W/kg, far-term thin-film) AND a light thruster (<=~2-4 kg/kW vs\n"
        "   ~6 today); achV saturates ~38 km/s. Feasibility is power-INDEPENDENT (alpha scales the\n"
        "   probe, not the margin); optimal Isp ~2800-3500 s. This is the optimistic mirror of the\n"
        "   nuclear closer (low alpha ~23 W/kg, near-term masses, optimistic reactor)."
    )

    # ---------------------------------------------------------------
    header("7c. PERIHELION PUMPING (multi-revolution escape)")
    from fermi_sim.departure import perihelion_pumped_vinf
    print("The outward-spiral saturation (sec 7) is a property of the TRAJECTORY CLASS, not of solar")
    print("power. Perihelion pumping inverts the spiral: retrograde arcs near apoapsis drop")
    print("perihelion to 0.42 AU (the thermal cap), then prograde arcs at perihelion (power 4x the")
    print("1-AU rating + max Oberth leverage) staircase the energy up over a few revolutions.")
    print("Integrated with a bang-bang policy (escape-guarded staircase + continuous finisher),")
    print("power P(r) = P1*min((1AU/r)^2, 4):\n")
    tgt = 23.64e3
    for a0 in (1.5e-4, 2.5e-4, 5.0e-4):
        v, dv, yr, revs = perihelion_pumped_vinf(a0, tgt)
        tag = "REACHES the cruise floor" if v >= tgt * 0.999 else "short"
        print(f"   a0={a0:.1e} m/s^2: v_inf {v/KMS:5.2f} km/s  dv {dv/KMS:5.2f}  "
              f"{yr:4.1f} yr  {revs:4.1f} revs   {tag}")
    print(
        "\n=> Pumping defeats the 1/r^2 power wall. At a0=2.5e-4 (~vehicle alpha 15-21 W/kg for\n"
        "   the mass ratios the maneuver itself allows -- TODAY'S hardware) the cruise floor is\n"
        "   reached where the outward spiral saturates near zero. The contiguous working region\n"
        "   starts at a0 ~ 2.24e-4; below it the bang-bang policy is PHASING-SENSITIVE, not simply\n"
        "   dead (a success island near 1.75-1.88e-4, strand bands at 1.9-2.2e-4 and ~2.9-3.1e-4\n"
        "   where the escaping pass strands below target -- gate designs by integration, and note\n"
        "   a stronger vehicle can always throttle to a working profile).\n"
        "   This bang-bang policy spends ~25.6 km/s; an optimised burn schedule reaches ~24. The\n"
        "   sec-7b alpha >~ 100 W/kg threshold applies to the OUTWARD-SPIRAL class only. The full\n"
        "   SEP total from LEO is ~30-32 km/s (7.6 Earth escape + ~23-24 helio), indicating our\n"
        "   closed-form low-thrust budget (~25-26 for AC) underprices the heliocentric\n"
        "   leg; a GTO drop-off cuts the Earth leg 7.6 -> ~4.2 km/s and closes a ~100 kg vehicle."
    )

    # ---------------------------------------------------------------
    header("7d. PERIHELION SYNCHROTRON -- the 'lasso idea' (external EM station)")
    from fermi_sim.departure import synchrotron_escape
    print("A fixed, externally powered EM station at perihelion 'lassoes' a PASSIVE probe once per")
    print("orbit with an impulsive prograde kick (no onboard propellant/power -- bypasses the rocket")
    print("equation; the accelerator is reused). NOT a true synchrotron: the period grows after every")
    print("kick, and ESCAPE TERMINATES RECIRCULATION -- the escaping kick must land >= v_p,target or")
    print("the probe is gone too slow. Fixed equal kicks, circular start at the station:\n")
    for rp, dv in ((10.0, 5e3), (20.0, 5e3), (10.0, 2e3), (215.03, 5e3)):
        s = synchrotron_escape(rp, dv, 23.64e3)
        tag = ("REACHES" if s["reached"]
               else f"GONE TOO SLOW @ {s['v_inf_final']/KMS:.1f}" if s["escaped_below"] else "short")
        rp_lbl = "1 AU  " if rp > 200 else f"{rp:4.0f} Rs"
        print(f"   {rp_lbl} kick {dv/KMS:3.0f} km/s: {s['passes']:3d} passes  "
              f"accel {s['time_yr']:5.1f} yr  max orbit {s['max_period_yr']:5.1f} yr  "
              f"dv_final_min {s['dv_final_min']/KMS:4.2f}   {tag}")
    print(
        "\n=> Deep stations win the endgame (dv_final_min ~1.4 km/s at 10 Rs vs ~6.2 at 1 AU) but face\n"
        "   continuous deep-solar exposure, ~57 km/s aperture rendezvous, phase-resonant orbit\n"
        "   ladders, and kick recoil. Equal kicks usually escape BELOW target; the strong form is a\n"
        "   ONE-KICK GATEWAY at ~4-10 Rs reused across a fleet of passive probes."
    )

    # ---------------------------------------------------------------
    header("8. VERDICT (conservative)")
    print(
        "* The mission CLOSES, but the conservative power gate settles it, and it reduces to ONE\n"
        "  number: the whole-vehicle specific power alpha = power/dry_mass. At today's specific\n"
        "  masses (alpha ~20-30 W/kg) pure solar-electric does NOT reach the 23.4 km/s floor.\n"
        "* Closing architectures:\n"
        "    - NUCLEAR-ELECTRIC ion (constant power): closes at LOW alpha (~23 W/kg) with near-term\n"
        "      specific masses but an optimistic ~40 W/kg reactor; ~5 kW + gridded ion -> ~24.8 km/s.\n"
        "    - HIGH-ALPHA SOLAR-ELECTRIC: pure solar DOES close above alpha ~ 100 W/kg -- an ultralight\n"
        "      ~50 kg micro-probe (>=~300 W/kg array + ~2 kg/kW thruster, Isp ~3000 s) burns briefly\n"
        "      near 1 AU and dodges the fade (-> ~37 km/s). Far-term tech, but no reactor, no assist.\n"
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
