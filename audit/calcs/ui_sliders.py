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
    "T": 72800, "pay": 1, "alt": 590, "injerr": 0.5, "gncerr": 2, "kstruct": 10, "isp": 3000, "eta": 0.5,
    "enginekg": 4, "tankfrac": 2.5, "pwrkw": 2, "cellEff": 30, "wkgsolar": 1000, "rtg": 40, "rp": 6,
    "srp": 10, "skick": 5,
}
RADIO_DEFAULTS = {"pwr": "solar", "ga": "pumped"}

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
          pwrW:r.pwrW, arraySpecPower:r.arraySpecPower, pumpInfo:r.pumpInfo, syn:r.syn};
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

    # GUARD: the page's NATIVE on-load defaults (the HTML value= attributes / selected radios), read
    # BEFORE any reset — this is what a fresh visitor sees. comp() overrides the sliders, so it would
    # NOT catch a mismatch between the DEFAULTS dict and the actual value= attributes (e.g. a slider
    # left at a stale value). The default design must be feasible on a pristine load.
    native = page.evaluate("""() => { const r = compute();
      return {feasible:r.feasible, achV:r.achievableVinf, floor:r.vinfSun,
              wkgsolar:+document.getElementById('wkgsolar').value,
              enginekg:+document.getElementById('enginekg').value, isp:+document.getElementById('isp').value}; }""")
    check("page NATIVE on-load default is FEASIBLE (value= attributes, no reset)",
          native["feasible"] is True,
          f"achV={native['achV']/1e3:.1f} vs floor {native['floor']/1e3:.1f}; "
          f"loaded wkgsolar={native['wkgsolar']} enginekg={native['enginekg']} isp={native['isp']}")

    base = comp()
    # The DEFAULT is now the high-α solar feasible design (build 68): 400 W/kg array + 3 kg/kW thruster
    # + Isp 3000 → vehicle α ≈ 118 W/kg → pure solar CLOSES with a ~3-4 km/s margin.
    check("default high-α solar IS feasible", base["feasible"] is True, base["infeasReason"])
    check("default is pure solar-electric (power-feasible)", base["powerFeasible"] is True)
    check("default achievable v∞ clears the floor", base["achievableVinf"] >= base["vinf"],
          f"{base['achievableVinf']/1e3:.1f} >= {base['vinf']/1e3:.1f} km/s")
    check("default vehicle α is in the closing corner (~100-130 W/kg)",
          100 < base["pwrW"]/base["dryEff"] < 135, f"{base['pwrW']/base['dryEff']:.0f} W/kg")
    # DEFAULT-STATE COHERENCE (the build-131-135 miss class): the default pumped campaign KPI must
    # show the validated reference campaign, and be pinned regardless of the Isp slider.
    check("default pumped campaign is the validated reference (4.9 revs, 9.6 yr, 25.6 dv)",
          base["pumpInfo"] is not None
          and abs(base["pumpInfo"]["revs"] - 4.9) < 0.2
          and abs(base["pumpInfo"]["years"] - 9.6) < 0.3
          and abs(base["pumpInfo"]["dv"]/1e3 - 25.6) < 0.2,
          str(base["pumpInfo"] and (round(base["pumpInfo"]["revs"],2), round(base["pumpInfo"]["years"],2))))
    # ENVELOPE PIN: the pumped campaign is flown at min(a0, 2.5e-4)/Isp 2800, so moving the Isp
    # slider must NOT change the campaign (the default vehicle a0 >> 2.5e-4, so it is throttled).
    isp_lo = comp({"isp": 2300}); isp_hi = comp({"isp": 4500})
    check("pumped campaign is Isp-pinned (2300 vs 4500 give the same campaign)",
          isp_lo["pumpInfo"] and isp_hi["pumpInfo"]
          and abs(isp_lo["pumpInfo"]["revs"] - isp_hi["pumpInfo"]["revs"]) < 1e-6
          and abs(isp_lo["pumpInfo"]["dv"] - isp_hi["pumpInfo"]["dv"]) < 1e-3,
          f"{isp_lo['pumpInfo'] and round(isp_lo['pumpInfo']['revs'],3)} vs {isp_hi['pumpInfo'] and round(isp_hi['pumpInfo']['revs'],3)}")
    # The direct outward-spiral reference architecture (the pumped default replaces it as the
    # page default, but the spiral physics checks below are about the direct trajectory class).
    direct = comp(radio={"ga": "direct"})
    # Drop α below the threshold (heavy conservative array + thruster) → the DIRECT spiral no longer closes.
    lowalpha = comp({"wkgsolar": 91, "enginekg": 6, "pwrkw": 5}, {"ga": "direct"})
    check("conservative low-α solar (91 W/kg, 6 kg/kW) does NOT close the direct spiral", lowalpha["feasible"] is False,
          f"α={lowalpha['pwrW']/lowalpha['dryEff']:.0f} W/kg")
    check("low-α infeasibility is the power-fade reason", "power-limited" in lowalpha["infeasReason"])
    check("solar-Oberth (Jupiter) departure DOES close", comp(radio={"ga": "oberth"})["feasible"] is True)
    # EP-ONLY closure: nuclear-electric is CONSTANT power (no 1/r² fade) — closes at low α too.
    nep = comp({"isp": 3000, "rtg": 40, "wkgsolar": 91, "enginekg": 6, "pwrkw": 5}, {"pwr": "nuclear", "ga": "direct"})
    check("nuclear-electric (constant power) DOES close — the low-α EP path", nep["feasible"] is True,
          f"achV={nep['achievableVinf']/1e3:.1f} vs floor {nep['vinf']/1e3:.1f} km/s")
    check("default arrival ~72.8k", abs(base["arrivalYr"] - 72800) < 400, str(base["arrivalYr"]))
    # Pumped budget prices v∞ + plane change with no Earth borrow, so its fuel optimum sits at
    # the ecliptic crossing (~79.3k), not the direct model's 72.8k Earth-borrow optimum.
    check("pumped fuel optimum sits at the ecliptic crossing (~79.3k)",
          abs(base["minFuelYr"] - 79250) < 600, f"{base['minFuelYr']:.0f}")
    check("direct fuel optimum stays ~72.8k", abs(direct["minFuelYr"] - 72800) < 400, f"{direct['minFuelYr']:.0f}")

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
    check("pumped fuel optimum stays ~79.3k regardless of aim", abs(a58["minFuelYr"]-79250) < 600 and abs(a100["minFuelYr"]-79250) < 600)
    check("more out-of-plane ⇒ more propellant", a58["mp"] > base["mp"])

    # --- DERIVED low-thrust departure Δv (no penalty knob anymore) ---
    # CONSERVATIVE pure-EP departure: build v∞ on the heliocentric spiral (v∞ + ~6 km/s tax) + the
    # plane-change penalty — ~30 km/s at the optimum, NOT the optimistic 25 km/s Earth-borrow spiral.
    check("direct design Δv at default 590 circular is the conservative heliocentric EP departure (~30 km/s)",
          abs(direct["dvDesign"]/1e3 - 29.8) < 0.6, f"{direct['dvDesign']/1e3:.2f}")
    # Pumped default: √(μ⊕/a) escape + v∞ + plane change + 2 km/s tax (+ margins) ≈ 34.3 km/s
    check("pumped default design Δv is the two-leg budget (~34.3 km/s)",
          abs(base["dvDesign"]/1e3 - 34.3) < 0.6, f"{base['dvDesign']/1e3:.2f}")
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
    ce = comp({"cellEff": 34})
    check("cell eff↑ shrinks array AREA", ce["arrayArea"] < base["arrayArea"])
    check("cell eff↑ leaves array MASS unchanged (mass set by W/kg)", rel(ce["arrayMass"], base["arrayMass"], 1e-6))
    wk_lo = comp({"wkgsolar": 300}); wk_hi = comp({"wkgsolar": 1200})
    check("array W/kg↑ lowers array mass", wk_hi["arrayMass"] < wk_lo["arrayMass"])
    check("array W/kg sets the array specific power directly", abs(wk_hi["arraySpecPower"] - 1200) < 1e-6)
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
    check("Jupiter assist lowers required Δv (vs direct)", jup["dvDesign"] < direct["dvDesign"] - 1000)
    obe = comp(radio={"ga": "oberth"})
    check("Oberth changes required Δv", not rel(obe["dvDesign"], base["dvDesign"], 1e-3))
    # Perihelion-pumped SEP: two-leg budget (no Earth borrow) is COSTLIER in Δv than the
    # Earth-borrow spiral, but the gate becomes the pumping staircase, which closes at
    # low-α (today's hardware) where the outward spiral saturates near zero.
    pmp = comp(radio={"ga": "pumped"})
    check("pumped budget = escape + v_inf + plane + tax (> direct budget)", pmp["dvDesign"] > direct["dvDesign"] + 1000,
          f"{pmp['dvDesign']/1e3:.1f} vs {direct['dvDesign']/1e3:.1f} km/s")
    low_alpha_direct = comp({"wkgsolar": 91, "enginekg": 6, "pwrkw": 50}, {"ga": "direct"})
    low_alpha_pumped = comp({"wkgsolar": 91, "enginekg": 6, "pwrkw": 50}, {"ga": "pumped"})
    check("low-α outward spiral fails but PUMPING closes it (power wall defeated)",
          low_alpha_direct["feasible"] is False and low_alpha_pumped["feasible"] is True,
          f"pumped achievable {low_alpha_pumped['achievableVinf']/1e3:.1f} km/s")
    check("pumped gate reports the campaign (revs > 1, powered years > 1)",
          low_alpha_pumped["pumpInfo"] is not None and low_alpha_pumped["pumpInfo"]["revs"] > 1
          and low_alpha_pumped["pumpInfo"]["years"] > 1)
    # Perihelion synchrotron ("lasso"): external station kicks — probe carries only a trim
    # budget, so the wet mass collapses; feasibility is the escape-termination rule.
    lasso = comp(radio={"ga": "synchro"})
    check("lasso: probe Δv is a trim budget only (< 2 km/s)", lasso["dvDesign"] < 2000,
          f"{lasso['dvDesign']/1e3:.2f} km/s")
    check("lasso: default 10 R☉ / 5 km/s campaign closes (12 kicks)",
          lasso["feasible"] is True and lasso["syn"] is not None and lasso["syn"]["passes"] == 12,
          f"passes={lasso['syn'] and lasso['syn']['passes']}")
    check("lasso: propellant fraction collapses (trim only, f < 5%) and wet mass drops",
          lasso["f"] < 0.05 and lasso["wet"] < 0.5 * base["wet"],
          f"f={100*lasso['f']:.1f}%, wet {lasso['wet']:.0f} vs {base['wet']:.0f} kg")
    lasso_weak = comp(radio={"ga": "synchro"}, over={"skick": 2})
    check("lasso: 2 km/s kicks escape below target (gone too slow → infeasible)",
          lasso_weak["feasible"] is False and lasso_weak["syn"]["escapedBelow"] is True,
          f"stranded v∞={lasso_weak['syn']['vInfFinal']/1e3:.1f} km/s")

    # --- FEASIBILITY transitions ---
    lowisp = comp({"isp": 1000})
    check("Isp=1000 → mass diverges (NOT feasible)", lowisp["feasible"] is False and lowisp["massConverges"] is False)
    nuc_opt = comp({"isp": 3000, "rtg": 40}, {"pwr": "nuclear", "ga": "direct"})
    check("derived dry mass is leaner than the old 255 kg bus (nuclear closer)", nuc_opt["dry"] < 255, f"{nuc_opt['dry']:.0f} kg dry")
    check("reset returns to the feasible high-α solar default", comp()["feasible"] is True)
    # Feasibility is set by vehicle α, NOT power: at the default α the design closes at any power
    # (power just scales the probe), and drops below the floor only when α falls (heavy components).
    check("default α closes at 50 kW too (power-independent)", comp({"pwrkw": 50})["feasible"] is True)
    check("low-α (91 W/kg array, 6 kg/kW) does NOT close the direct spiral even at 50 kW", comp({"wkgsolar": 91, "enginekg": 6, "pwrkw": 50}, {"ga": "direct"})["feasible"] is False)
    # The two levers must move together: a concentrator array with a HEAVY engine still fails (low α),
    # but with a light engine it closes — α is the binding variable.
    conc_heavy = comp({"wkgsolar": 486, "enginekg": 8}, {"ga": "direct"})
    check("concentrator + heavy 8 kg/kW engine still does NOT close the direct spiral (low α)", conc_heavy["feasible"] is False,
          f"α={conc_heavy['pwrW']/conc_heavy['dryEff']:.0f} W/kg")
    conc_light = comp({"wkgsolar": 486, "enginekg": 2}, {"ga": "direct"})
    check("concentrator + light 2 kg/kW engine DOES close the direct spiral (high α)", conc_light["feasible"] is True,
          f"α={conc_light['pwrW']/conc_light['dryEff']:.0f} W/kg")

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
