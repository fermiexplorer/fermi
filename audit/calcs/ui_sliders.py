#!/usr/bin/env python3
"""Comprehensive UI behaviour test for the Fermi Explorer calculator.

Drives every slider / dropdown / radio in index.html and asserts that each input
moves the *right* derived quantities in the *right* direction — and, just as important,
that it does NOT move the ones it shouldn't (e.g. dry mass must not change the arrival
time or the propellant fraction). It calls the page's own compute() so the assertions
run against the real model, not a copy.

Run:  .venv/bin/python audit/calcs/ui_sliders.py
Needs: playwright (.venv/bin/pip install playwright && .venv/bin/playwright install chromium)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PORT = 8079
URL = f"http://127.0.0.1:{PORT}/index.html"

# default control values (must match index.html)
DEFAULTS = {
    "T": 72800, "pay": 1, "alt": 590, "injerr": 0.5, "gncerr": 2, "kstruct": 10, "isp": 1585, "eta": 0.5,
    "enginekg": 6, "tankfrac": 2.5, "pwrkw": 5, "cellEff": 20, "wkgsolar": 91, "rtg": 40, "rp": 6,
}
RADIO_DEFAULTS = {"pwr": "solar", "ga": "direct"}

# JS: reset everything to defaults, apply overrides, return compute()
RESET_AND_COMPUTE = """
(args) => {
  const [defs, radioDefs, over, radioOver] = args;
  for (const [k,v] of Object.entries(defs)) document.getElementById(k).value = v;
  document.getElementById('propsel').value = 'Xenon|2.5|131.29';
  for (const [k,v] of Object.entries(radioDefs)) document.querySelector(`input[name=${k}][value="${v}"]`).checked = true;
  for (const [k,v] of Object.entries(over)) document.getElementById(k).value = v;
  for (const [k,v] of Object.entries(radioOver)) document.querySelector(`input[name=${k}][value="${v}"]`).checked = true;
  const r = compute();
  return {dvDesign:r.dvDesign, mp:r.mp, wet:r.wet, f:r.f, arrivalYr:r.arrivalYr,
          tiltDeg:r.tiltDeg, tiltAbs:Math.abs(r.tiltDeg), vinf:r.vinfSun, minFuelYr:r.minFuelYr,
          minWet:r.minWet, thrust:r.thrust, burnYr:r.burnYr, E:r.E, arrayArea:r.arrayArea,
          arrayMass:r.arrayMass, engineMass:r.engineMass, tankMass:r.tankMass,
          busPayload:r.busPayload, dryEff:r.dryEff, psLabel:r.psLabel, feasible:r.feasible, isp:r.isp,
          achievableVinf:r.achievableVinf, powerFeasible:r.powerFeasible, infeasReason:r.infeasReason,
          dry:r.dry, structureMass:r.structureMass, massConverges:r.massConverges, active:r.active,
          pwrW:r.pwrW, arraySpecPower:r.arraySpecPower};
}
"""

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not ok else ""))

def rel(a, b, tol=1e-6):  # approx equal
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))

def run(page):
    def comp(over=None, radio=None):
        return page.evaluate(RESET_AND_COMPUTE, [DEFAULTS, RADIO_DEFAULTS, over or {}, radio or {}])

    base = comp()
    # sanity on the default design — CONSERVATIVE: pure solar-electric is power-limited (1/r² fade)
    # and does NOT close; this is the intended headline, not a bug.
    check("default pure-SEP is NOT feasible (power-limited)", base["feasible"] is False)
    check("default infeasibility is the power-fade reason", "power-limited" in base["infeasReason"])
    check("default achievable v∞ saturates below the floor", base["achievableVinf"] < base["vinf"],
          f"{base['achievableVinf']/1e3:.1f} < {base['vinf']/1e3:.1f} km/s")
    check("solar-Oberth (Jupiter) departure DOES close", comp(radio={"ga": "oberth"})["feasible"] is True)
    # EP-ONLY closure: nuclear-electric is CONSTANT power (no 1/r² fade), so the spiral reaches the
    # floor where solar cannot. The closing pure-electric design is ~5 kW reactor + gridded ion.
    nep = comp({"isp": 3000, "rtg": 40}, {"pwr": "nuclear", "ga": "direct"})
    check("pure-EP nuclear-electric (5 kW, gridded ion) DOES close — the EP-only path", nep["feasible"] is True,
          f"achV={nep['achievableVinf']/1e3:.1f} vs floor {nep['vinf']/1e3:.1f} km/s, feasible={nep['feasible']}")
    check("nuclear-electric reaches the floor (constant power, no fade)", nep["powerFeasible"] is True,
          f"{nep['achievableVinf']/1e3:.1f} >= {nep['vinf']/1e3:.1f}")
    check("solar at the same Isp/power still does NOT close (1/r² fade)",
          comp({"isp": 3000}, {"pwr": "solar", "ga": "direct"})["feasible"] is False)
    check("default arrival ~72.8k", abs(base["arrivalYr"] - 72800) < 400, str(base["arrivalYr"]))
    check("default arrival sits at the fuel optimum", abs(base["arrivalYr"] - base["minFuelYr"]) < 600, f"{base['arrivalYr']:.0f} vs {base['minFuelYr']:.0f}")

    # --- PAYLOAD: must raise propellant & wet, but NOT arrival / Δv / fraction ---
    p = comp({"pay": 50})
    check("payload↑ raises xenon (mp)", p["mp"] > base["mp"] + 5, f"{base['mp']:.0f}->{p['mp']:.0f}")
    check("payload↑ raises wet mass", p["wet"] > base["wet"] + 5)
    check("payload↑ leaves Δv unchanged", rel(p["dvDesign"], base["dvDesign"], 1e-3))
    check("payload↑ leaves arrival unchanged", p["arrivalYr"] == base["arrivalYr"])
    check("payload↑ leaves propellant FRACTION unchanged", rel(p["f"], base["f"], 1e-3))
    # derived dry: +49 kg payload drags propellant + structure, so dry_eff rises by MORE than 49 kg
    check("payload↑ raises dryEff (amplified by the derived sizing)", p["dryEff"] > base["dryEff"] + 49)

    # --- BUS STRUCTURE FRACTION: raises structure → dry → wet (use Isp 3000 so the mass converges) ---
    s0 = comp({"isp": 3000, "kstruct": 5}); d = comp({"isp": 3000, "kstruct": 20})
    check("structure frac↑ raises structure mass", d["structureMass"] > s0["structureMass"] + 5)
    check("structure frac↑ raises dry mass", d["dry"] > s0["dry"] + 5)
    check("structure frac↑ raises wet mass", d["wet"] > s0["wet"] + 5)
    check("structure frac↑ leaves arrival unchanged", d["arrivalYr"] == s0["arrivalYr"])
    check("structure frac↑ leaves Δv unchanged", rel(d["dvDesign"], s0["dvDesign"], 1e-3))

    # --- ISP: higher Isp ⇒ less propellant & fraction, less thrust, lighter (derived) vehicle ---
    i = comp({"isp": 4500})
    check("Isp↑ lowers xenon", i["mp"] < base["mp"] - 5)
    check("Isp↑ lowers propellant fraction", i["f"] < base["f"] - 0.02)
    check("Isp↑ lowers thrust", i["thrust"] < base["thrust"])
    check("Isp↑ lowers wet mass (derived dry shrinks with less propellant)", i["wet"] < base["wet"])
    check("Isp↑ leaves arrival/Δv unchanged", i["arrivalYr"] == base["arrivalYr"] and rel(i["dvDesign"], base["dvDesign"], 1e-3))

    # --- ARRIVAL TIME: drives tilt, Δv, fuel; optimum & 79k crossing behaviour ---
    a58 = comp({"T": 58000}); a79 = comp({"T": 79000}); a100 = comp({"T": 100000})
    check("T=58k is ~10° out of plane", abs(a58["tiltAbs"] - 10.1) < 0.5, f"{a58['tiltAbs']:.1f}")
    check("T=79k is ~0° (ecliptic crossing)", a79["tiltAbs"] < 0.5, f"{a79['tiltAbs']:.2f}")
    check("T=58k costs more Δv than optimum", a58["dvDesign"] > base["dvDesign"] + 200)
    check("T=100k costs more Δv than optimum", a100["dvDesign"] > base["dvDesign"] + 200)
    check("Δv is flat between 73k and 79k (<2%)", abs(a79["dvDesign"]-base["dvDesign"])/base["dvDesign"] < 0.02)
    check("fuel optimum stays ~72.8k regardless of aim", abs(a58["minFuelYr"]-72800) < 400 and abs(a100["minFuelYr"]-72800) < 400)
    check("more out-of-plane ⇒ more propellant", a58["mp"] > base["mp"])

    # --- DERIVED low-thrust departure Δv (no penalty knob anymore) ---
    # CONSERVATIVE pure-EP departure: build v∞ on the heliocentric spiral (v∞ + ~6 km/s tax) + the
    # plane-change penalty — ~30 km/s at the optimum, NOT the optimistic 25 km/s Earth-borrow spiral.
    check("design Δv at default 590 circular is the conservative heliocentric EP departure (~30 km/s)",
          abs(base["dvDesign"]/1e3 - 29.8) < 0.6, f"{base['dvDesign']/1e3:.2f}")
    check("design Δv > impulsive floor (low-thrust costs more)", base["dvDesign"]/1e3 > 20)
    check("58k aim costs more derived Δv than the 73k optimum", a58["dvDesign"] > base["dvDesign"])

    # --- STARTING ORBIT: circular LEO only (elliptical option removed) ---
    # A higher circular orbit carries more energy → slightly less ion Δv to spiral out.
    alt2000 = comp({"alt": 2000})
    check("higher circular orbit lowers Δv (more orbital energy)", alt2000["dvDesign"] < base["dvDesign"], f"{alt2000['dvDesign']/1e3:.2f} vs {base['dvDesign']/1e3:.2f} km/s")

    # --- NAVIGATION MARGINS: injection + GNC pointing errors add Δv and xenon ---
    perfect = comp({"injerr": 0, "gncerr": 0})
    check("zero pointing errors → lowest departure Δv (baseline)", perfect["dvDesign"] < base["dvDesign"])
    inj3 = comp({"injerr": 3, "gncerr": 0})
    check("injection pointing error raises Δv", inj3["dvDesign"] > perfect["dvDesign"] + 100)
    check("injection pointing error raises xenon", inj3["mp"] > perfect["mp"])
    gnc10 = comp({"injerr": 0, "gncerr": 10})
    check("GNC pointing error raises Δv (cosine loss)", gnc10["dvDesign"] > perfect["dvDesign"])
    check("GNC pointing error raises xenon", gnc10["mp"] > perfect["mp"])

    # --- POWER: thrust, burn time, array size ---
    pw = comp({"pwrkw": 12})
    check("power↑ raises thrust", pw["thrust"] > base["thrust"])
    check("power↑ shortens burn", pw["burnYr"] < base["burnYr"])
    check("power↑ enlarges array (area & mass)", pw["arrayArea"] > base["arrayArea"] and pw["arrayMass"] > base["arrayMass"])
    check("power↑ leaves Δv & arrival unchanged", rel(pw["dvDesign"], base["dvDesign"], 1e-3) and pw["arrivalYr"] == base["arrivalYr"])

    # --- THRUSTER EFFICIENCY ---
    e = comp({"eta": 0.8})
    check("efficiency↑ raises thrust", e["thrust"] > base["thrust"])
    check("efficiency↑ lowers electrical energy", e["E"] < base["E"])

    # --- SOLAR CELL EFFICIENCY (sets AREA) / SPECIFIC POWER (sets MASS) ---
    ce = comp({"cellEff": 30})
    check("cell eff↑ shrinks array AREA", ce["arrayArea"] < base["arrayArea"])
    check("cell eff↑ leaves array MASS unchanged (mass set by W/kg)", rel(ce["arrayMass"], base["arrayMass"], 1e-6))
    wk = comp({"wkgsolar": 300})
    check("array W/kg↑ lowers array mass", wk["arrayMass"] < base["arrayMass"])
    check("array W/kg↑ sets the array specific power directly", abs(wk["arraySpecPower"] - 300) < 1e-6)
    # whole-vehicle specific power KPI = P / dry_eff
    veh = comp({"isp": 3000}, {"pwr": "nuclear", "ga": "direct"})
    check("vehicle specific power ~ P/dryEff (nuclear closer ~20-30 W/kg)",
          18 < veh["pwrW"]/veh["dryEff"] < 30, f"{veh['pwrW']/veh['dryEff']:.1f} W/kg")

    # --- ENGINE kg/kW and TANK % feed the derived dry mass ---
    en = comp({"enginekg": 12})
    check("engine kg/kW↑ raises engine mass", en["engineMass"] > base["engineMass"])
    check("engine kg/kW↑ raises derived dry mass", en["dry"] > base["dry"])
    tk = comp({"tankfrac": 20})
    check("tank %↑ raises tank mass", tk["tankMass"] > base["tankMass"])

    # --- PROPELLANT choice couples to effective Isp (lighter ion -> higher Isp -> less fuel) ---
    ar = comp({"propsel": "Argon|6|39.95"})
    check("Argon -> ~1.81x effective Isp vs Xenon", abs(ar["isp"]/base["isp"] - 1.81) < 0.05, f"{ar['isp']/base['isp']:.2f}x")
    check("Argon -> lower propellant fraction than Xenon", ar["f"] < base["f"] - 0.05, f"{base['f']:.2f}->{ar['f']:.2f}")

    # --- POWER SOURCE radio ---
    fc = comp(radio={"pwr": "fuelcell"}); nu = comp(radio={"pwr": "nuclear"})
    check("power source = fuel cell relabels", "Fuel-cell" in fc["psLabel"])
    check("power source = reactor relabels", nu["psLabel"] == "Reactor")

    # --- ARCHITECTURE radio ---
    jup = comp(radio={"ga": "jupiter"})
    check("Jupiter assist lowers required Δv", jup["dvDesign"] < base["dvDesign"] - 1000)
    obe = comp(radio={"ga": "oberth"})
    check("Oberth changes required Δv", not rel(obe["dvDesign"], base["dvDesign"], 1e-3))

    # --- FEASIBILITY transitions ---
    lowisp = comp({"isp": 1000})
    check("Isp=1000 → mass diverges (NOT feasible)", lowisp["feasible"] is False and lowisp["massConverges"] is False)
    nuc_opt = comp({"isp": 3000, "rtg": 40}, {"pwr": "nuclear", "ga": "direct"})
    check("derived dry mass is leaner than the old 255 kg bus (nuclear closer)", nuc_opt["dry"] < 255, f"{nuc_opt['dry']:.0f} kg dry")
    check("reset returns to the conservative (power-limited) default", comp()["feasible"] is False)
    # the coupled trap: more power → either still below the floor (power) or the array breaks the
    # mass budget — pure-SEP does not close at any setting on the default bus.
    check("even 50 kW pure-SEP still does not close (coupled power/mass)", comp({"pwrkw": 50})["feasible"] is False)
    # A big, LIGHT (concentrator) array raises achievable v∞ but still does NOT close: reaching the
    # floor under 1/r² fade needs ~30-80 kW, and the thruster/PPU (6 kg/kW) + propellant mass at that
    # power break the dry-bus budget. The array's specific power is not the binding constraint.
    conc = comp({"cellEff": 25, "wkgsolar": 486, "pwrkw": 60})  # concentrator (~486 W/kg), 60 kW
    check("concentrator + 60 kW still does not close solar (engine+propellant mass)", conc["feasible"] is False,
          f"achV={conc['achievableVinf']/1e3:.1f} km/s, bus={conc['busPayload']:.0f} kg, feasible={conc['feasible']}")

def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    errors = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append("PAGEERR: " + str(e)))
            pg.goto(URL, wait_until="networkidle")
            pg.wait_for_timeout(1000)
            print("== Fermi Explorer UI slider behaviour test ==")
            run(pg)
            check("no JavaScript console/page errors", not errors, "; ".join(errors[:5]))
            b.close()
    finally:
        srv.terminate()
    npass = sum(1 for _, ok, _ in results if ok)
    print("-" * 60)
    print(f"UI SLIDERS: {npass}/{len(results)} checks passed")
    sys.exit(0 if npass == len(results) else 1)

if __name__ == "__main__":
    main()
