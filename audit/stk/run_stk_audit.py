#!/usr/bin/env python3
"""Fermi independent audit — STK/Astrogator cross-validation driver (RUNS ON WINDOWS).

Builds and runs the two departure checks (the same config the NASA GMAT audit uses,
see ../gmat/) in Ansys STK's Astrogator, then writes out/stk_results.json for
../stk/compare.py:

  CHECK 1 — impulsive (Oberth) departure:
      circular orbit r = 6771 km (Earth point mass), apply 14.633297 km/s along
      velocity  ->  post-burn C3 must equal 379.8154 km^2/s^2 (= v_inf,Earth^2).

  CHECK 2 — low-thrust Earth-escape spiral:
      same orbit, constant tangential thrust 0.5 N on a 1000 kg spacecraft with a
      huge Isp (1e7 s, so the acceleration stays ~5e-4 m/s^2), burn until C3 = 0
      ->  escape time must be ~1.42657e7 s (~692 revolutions).

Requirements (Windows host, NOT WSL):
  * STK 12.x Desktop with an Astrogator license (the free trial includes it;
    the perpetual "STK Free" tier does NOT).
  * The STK Python API wheel that ships with the install:
        pip install "C:\\Program Files\\AGI\\STK 12\\bin\\AgPythonAPI\\agi.stk12-<ver>-py3-none-any.whl"
  * Run:  python run_stk_audit.py     (STK will open; the script drives it)

The STK object-model property names below follow the STK 12 Python API samples.
Minor names can drift between STK versions — every step is wrapped so a failure
tells you exactly which GUI setting to make by hand instead (see README.md,
"Manual GUI path"); the audit is then completed by filling out/stk_results.json.
"""
import json
import math
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# ---- shared config (identical to audit/gmat) ----
R0_KM = 6771.0                 # circular orbit radius (= 400 km altitude, R_earth 6371)
MU_STK = 398600.4415           # km^3/s^2 — STK's Earth GM (WGS84/EGM96 family). The engine
                               # uses 398600.4418; the 8e-7 relative difference is far
                               # below the comparison tolerances.
DV_KMS = 14.633297             # impulsive departure dv (fermi_sim, min-speed aim @ 58,138 yr)
THRUST_N = 0.5                 # check-2 thrust  -> a = 5e-4 m/s^2 on 1000 kg
ISP_S = 1.0e7                  # huge Isp => propellant draw ~0.07 kg, accel ~constant
DRY_KG, FUEL_KG = 999.0, 1.0
V_CIRC = math.sqrt(MU_STK / R0_KM)          # km/s
T_CAP_S = 3.0e7                # safety cap for the spiral (expected escape ~1.43e7 s)

results = {"config": {"r0_km": R0_KM, "dv_kms": DV_KMS, "thrust_N": THRUST_N,
                      "isp_s": ISP_S, "mass_kg": DRY_KG + FUEL_KG, "mu_km3s2": MU_STK}}


def die(step, exc):
    print(f"\n*** FAILED at step: {step}\n    {type(exc).__name__}: {exc}")
    print("    See README.md 'Manual GUI path' — make this setting in the STK GUI,")
    print("    run the MCS, and enter the results in out/stk_results.json by hand.")
    sys.exit(1)


try:
    from agi.stk12.stkdesktop import STKDesktop
    from agi.stk12.stkobjects import AgESTKObjectType, AgEVePropagatorType
    from agi.stk12.stkobjects.astrogator import (
        AgEVASegmentType, AgEVAAttitudeControl, AgEVAElementType,
        AgEVAStoppingConditionSign,
    )
except ImportError as e:
    print("STK Python API not installed. Install the wheel that ships with STK:")
    print(r'  pip install "C:\Program Files\AGI\STK 12\bin\AgPythonAPI\agi.stk12-*.whl"')
    sys.exit(1)

# ---------------------------------------------------------------- launch STK
try:
    print("Starting STK (this opens the desktop app)…")
    stk = STKDesktop.StartApplication(visible=True, userControl=True)
    root = stk.Root
    root.NewScenario("FermiSTKAudit")
    scen = root.CurrentScenario
    scen.SetTimePeriod("1 Jan 2030 00:00:00.000", "1 Feb 2031 00:00:00.000")
except Exception as e:
    die("launch STK / new scenario", e)


def new_astrogator_sat(name):
    sat = scen.Children.New(AgESTKObjectType.eSatellite, name)
    sat.SetPropagatorType(AgEVePropagatorType.ePropagatorAstrogator)
    drv = sat.Propagator
    drv.MainSequence.RemoveAll()
    return sat, drv


def add_initial_state(mcs):
    """Circular equatorial orbit at r = 6771 km, Cartesian, Earth inertial."""
    seg = mcs.Insert(AgEVASegmentType.eVASegmentTypeInitialState, "Init", "-")
    seg.OrbitEpoch = scen.StartTime
    seg.SetElementType(AgEVAElementType.eVAElementTypeCartesian)
    el = seg.Element
    el.X, el.Y, el.Z = R0_KM, 0.0, 0.0
    el.Vx, el.Vy, el.Vz = 0.0, V_CIRC, 0.0
    sp = seg.SpacecraftParameters
    sp.DryMass = DRY_KG
    fu = seg.FuelTank
    fu.FuelMass = FUEL_KG
    return seg


def add_results(seg, names):
    """Attach Astrogator calc-object Results so values can be read after RunMCS."""
    for n in names:
        try:
            seg.Results.Add(n)
        except Exception as e:
            print(f"    (note: could not add result '{n}': {e} — will skip)")


# ======================================================================
# CHECK 1 — impulsive Oberth departure
# ======================================================================
try:
    print("CHECK 1: building impulsive-departure MCS…")
    sat1, drv1 = new_astrogator_sat("Probe1")
    mcs1 = drv1.MainSequence
    add_initial_state(mcs1)
    man = mcs1.Insert(AgEVASegmentType.eVASegmentTypeManeuver, "OberthKick", "-")
    man.SetManeuverType(0)  # 0 = eVAManeuverTypeImpulsive
    imp = man.Maneuver
    imp.SetAttitudeControlType(AgEVAAttitudeControl.eVAAttitudeControlThrustVector)
    tv = imp.AttitudeControl
    tv.ThrustAxesName = "Satellite VNC(Earth)"
    tv.DeltaVVector.AssignCartesian(DV_KMS, 0.0, 0.0)   # X = velocity direction in VNC
    add_results(man, ["Keplerian Elems/C3_Energy"])
    print("  running MCS…")
    drv1.RunMCS()
    c3 = float(man.GetResultValue("C3_Energy"))
    results["check1_c3_km2s2"] = c3
    print(f"  post-burn C3 = {c3:.4f} km^2/s^2   (expect 379.8154)")
except Exception as e:
    die("CHECK 1 (impulsive maneuver)", e)

# ======================================================================
# CHECK 2 — constant-tangential low-thrust escape spiral
# ======================================================================
try:
    print("CHECK 2: creating the constant-thrust engine model…")
    # Component Browser: duplicate the stock 'Constant Thrust and Isp' engine
    comp = root.CurrentScenario.ComponentDirectory.GetComponents(4)  # 4 = eComponentAstrogator
    engines = comp.GetFolder("Engine Models")
    src = engines.Item("Constant Thrust and Isp")
    try:
        eng = engines.DuplicateComponent("Constant Thrust and Isp", "FermiIon")
    except Exception:
        src.CloneObject()                       # older API name
        eng = engines.Item("FermiIon")
    eng.Thrust = THRUST_N                       # N
    eng.Isp = ISP_S                             # s
except Exception as e:
    die("CHECK 2 (engine model in Component Browser)", e)

try:
    print("CHECK 2: building finite-burn MCS…")
    sat2, drv2 = new_astrogator_sat("Probe2")
    mcs2 = drv2.MainSequence
    add_initial_state(mcs2)
    man2 = mcs2.Insert(AgEVASegmentType.eVASegmentTypeManeuver, "Spiral", "-")
    man2.SetManeuverType(1)  # 1 = eVAManeuverTypeFinite
    fin = man2.Maneuver
    fin.SetAttitudeControlType(AgEVAAttitudeControl.eVAAttitudeControlThrustVector)
    tv2 = fin.AttitudeControl
    tv2.ThrustAxesName = "Satellite VNC(Earth)"
    tv2.ThrustVector.AssignCartesian(1.0, 0.0, 0.0)     # thrust along velocity
    fin.SetPropulsionMethod(0, "FermiIon")               # 0 = engine model, by name
    prop = fin.Propagator
    prop.PropagatorName = "Earth Point Mass"             # stock Astrogator point-mass propagator
    sc = prop.StoppingConditions
    sc.Add("UserSelect")
    us = sc.Item("UserSelect").Properties
    us.UserCalcObjectName = "C3_Energy"                  # stop at C3 = 0 (escape)
    us.Trip = 0.0
    try:
        us.Sign = AgEVAStoppingConditionSign.eVAStoppingConditionSignIncreasing
    except Exception:
        pass
    dur = sc.Item("Duration").Properties if "Duration" in [sc.Item(i).Name for i in range(sc.Count)] else None
    if dur is None:
        sc.Add("Duration")
        dur = sc.Item("Duration").Properties
    dur.Trip = T_CAP_S                                   # safety cap
    add_results(man2, ["Keplerian Elems/C3_Energy", "Time/Duration", "Maneuver/DeltaV"])
    print("  running MCS (a ~700-revolution spiral — takes a while)…")
    drv2.RunMCS()
    t_esc = float(man2.GetResultValue("Duration"))
    results["check2_escape_s"] = t_esc
    try:
        results["check2_dv_kms"] = float(man2.GetResultValue("DeltaV"))
    except Exception:
        pass
    print(f"  escape time = {t_esc:.5e} s   (expect ~1.42657e7)")
except Exception as e:
    die("CHECK 2 (finite-burn spiral)", e)

# ----------------------------------------------------------------- write out
path = os.path.join(OUT, "stk_results.json")
with open(path, "w") as fh:
    json.dump(results, fh, indent=2)
print(f"\nwrote {path}")
print("Now run (on either Windows or WSL):  python compare.py")
