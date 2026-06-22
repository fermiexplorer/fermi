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
    "T": 72800, "pay": 1, "alt": 400, "dry": 255, "isp": 3000, "eta": 0.6,
    "enginekg": 6, "tankfrac": 8, "pwrkw": 5, "cellEff": 20, "areal": 3, "rtg": 5, "rp": 6,
}
RADIO_DEFAULTS = {"pwr": "solar", "ga": "direct"}

# JS: reset everything to defaults, apply overrides, return compute()
RESET_AND_COMPUTE = """
(args) => {
  const [defs, radioDefs, over, radioOver] = args;
  for (const [k,v] of Object.entries(defs)) document.getElementById(k).value = v;
  document.getElementById('propsel').value = 'Xenon|8|131.29';
  for (const [k,v] of Object.entries(radioDefs)) document.querySelector(`input[name=${k}][value="${v}"]`).checked = true;
  for (const [k,v] of Object.entries(over)) document.getElementById(k).value = v;
  for (const [k,v] of Object.entries(radioOver)) document.querySelector(`input[name=${k}][value="${v}"]`).checked = true;
  const r = compute();
  return {dvDesign:r.dvDesign, mp:r.mp, wet:r.wet, f:r.f, arrivalYr:r.arrivalYr,
          tiltDeg:r.tiltDeg, tiltAbs:Math.abs(r.tiltDeg), vinf:r.vinfSun, minFuelYr:r.minFuelYr,
          minWet:r.minWet, thrust:r.thrust, burnYr:r.burnYr, E:r.E, arrayArea:r.arrayArea,
          arrayMass:r.arrayMass, engineMass:r.engineMass, tankMass:r.tankMass,
          busPayload:r.busPayload, dryEff:r.dryEff, psLabel:r.psLabel, feasible:r.feasible, isp:r.isp};
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
    # sanity on the default design
    check("default is feasible", base["feasible"] is True)
    check("default arrival ~72.8k", abs(base["arrivalYr"] - 72800) < 400, str(base["arrivalYr"]))
    check("default arrival sits at the fuel optimum", abs(base["arrivalYr"] - base["minFuelYr"]) < 600, f"{base['arrivalYr']:.0f} vs {base['minFuelYr']:.0f}")

    # --- PAYLOAD: must raise propellant & wet, but NOT arrival / Δv / fraction ---
    p = comp({"pay": 50})
    check("payload↑ raises xenon (mp)", p["mp"] > base["mp"] + 5, f"{base['mp']:.0f}->{p['mp']:.0f}")
    check("payload↑ raises wet mass", p["wet"] > base["wet"] + 5)
    check("payload↑ leaves Δv unchanged", rel(p["dvDesign"], base["dvDesign"], 1e-3))
    check("payload↑ leaves arrival unchanged", p["arrivalYr"] == base["arrivalYr"])
    check("payload↑ leaves propellant FRACTION unchanged", rel(p["f"], base["f"], 1e-3))
    check("payload↑ raises dryEff by ~49 kg", abs((p["dryEff"]-base["dryEff"]) - 49) < 1)

    # --- DRY-BUS MASS: scales mp & wet, but NOT arrival / fraction / Δv ---
    d = comp({"dry": 400})
    check("dry↑ raises wet mass", d["wet"] > base["wet"] + 50)
    check("dry↑ raises xenon", d["mp"] > base["mp"] + 50)
    check("dry↑ leaves arrival unchanged", d["arrivalYr"] == base["arrivalYr"])
    check("dry↑ leaves propellant fraction unchanged", rel(d["f"], base["f"], 1e-3))
    check("dry↑ leaves Δv unchanged", rel(d["dvDesign"], base["dvDesign"], 1e-3))

    # --- ISP: higher Isp ⇒ less propellant & fraction, less thrust, more energy ---
    i = comp({"isp": 4500})
    check("Isp↑ lowers xenon", i["mp"] < base["mp"] - 5)
    check("Isp↑ lowers propellant fraction", i["f"] < base["f"] - 0.02)
    check("Isp↑ lowers thrust", i["thrust"] < base["thrust"])
    check("Isp↑ raises electrical energy E", i["E"] > base["E"])
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
    check("design Δv at default is the derived spiral (~25.1 km/s)", abs(base["dvDesign"]/1e3 - 25.12) < 0.3, f"{base['dvDesign']/1e3:.2f}")
    check("design Δv > impulsive floor (low-thrust costs more)", base["dvDesign"]/1e3 > 20)
    check("58k aim costs more derived Δv than the 73k optimum", a58["dvDesign"] > base["dvDesign"])

    # --- LEO ALTITUDE: changes the impulsive Oberth Δv ---
    alt2000 = comp({"alt": 2000})
    check("altitude changes Δv (Oberth)", not rel(alt2000["dvDesign"], base["dvDesign"], 1e-3))

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

    # --- SOLAR CELL EFFICIENCY / AREAL DENSITY ---
    ce = comp({"cellEff": 30})
    check("cell eff↑ shrinks array area & mass", ce["arrayArea"] < base["arrayArea"] and ce["arrayMass"] < base["arrayMass"])
    ar = comp({"areal": 5})
    check("areal density↑ raises array mass", ar["arrayMass"] > base["arrayMass"])

    # --- ENGINE kg/kW and TANK % eat the dry-bus margin ---
    en = comp({"enginekg": 12})
    check("engine kg/kW↑ raises engine mass", en["engineMass"] > base["engineMass"])
    check("engine kg/kW↑ cuts dry-bus margin", en["busPayload"] < base["busPayload"])
    tk = comp({"tankfrac": 20})
    check("tank %↑ raises tank mass", tk["tankMass"] > base["tankMass"])

    # --- PROPELLANT choice couples to effective Isp (lighter ion -> higher Isp -> less fuel) ---
    ar = comp({"propsel": "Argon|16|39.95"})
    check("Argon -> ~1.81x effective Isp vs Xenon", abs(ar["isp"]/base["isp"] - 1.81) < 0.05, f"{ar['isp']/base['isp']:.2f}x")
    check("Argon -> lower propellant fraction than Xenon", ar["f"] < base["f"] - 0.05, f"{base['f']:.2f}->{ar['f']:.2f}")

    # --- POWER SOURCE radio ---
    fc = comp(radio={"pwr": "fuelcell"}); nu = comp(radio={"pwr": "nuclear"})
    check("power source = fuel cell relabels", "Fuel-cell" in fc["psLabel"])
    check("power source = RTG relabels", nu["psLabel"] == "RTG")

    # --- ARCHITECTURE radio ---
    jup = comp(radio={"ga": "jupiter"})
    check("Jupiter assist lowers required Δv", jup["dvDesign"] < base["dvDesign"] - 1000)
    obe = comp(radio={"ga": "oberth"})
    check("Oberth changes required Δv", not rel(obe["dvDesign"], base["dvDesign"], 1e-3))

    # --- FEASIBILITY transitions ---
    lowisp = comp({"isp": 1000})
    check("Isp=1000 → NOT feasible (tank ceiling)", lowisp["feasible"] is False)
    heavy = comp({"pwrkw": 20, "dry": 80})
    check("20 kW on 80 kg bus → NOT feasible (mass)", heavy["feasible"] is False)
    check("returns to feasible after reset", comp()["feasible"] is True)

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
