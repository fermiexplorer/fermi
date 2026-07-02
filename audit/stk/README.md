# STK / Astrogator cross-validation (prep — awaiting an STK license)

An **independent** check of the Fermi departure model against
[Ansys STK](https://www.ansys.com/products/missions/ansys-stk) (Systems Tool Kit) with the
**Astrogator** trajectory-design module — the commercial industry-standard counterpart to the
[NASA GMAT cross-validation](../gmat/) already in this repo. Same two checks, same config,
so a pass gives **four-way agreement**: engine ↔ GMAT ↔ Fable (scipy) ↔ STK.

| Check | Config | Expected result |
|---|---|---|
| 1 — impulsive (Oberth) departure | circular orbit **r = 6771 km**, Earth **point mass**, apply **14.633297 km/s** along velocity | post-burn **C3 = 379.8154 km²/s²** (tol 0.05 %) |
| 2 — low-thrust escape spiral | same orbit, **0.5 N** constant tangential thrust, **1000 kg** (999 dry + 1 fuel), **Isp 10⁷ s** (→ accel ≈ 5×10⁻⁴ m/s², ~constant), burn to **C3 = 0** | escape time **≈ 1.42657×10⁷ s** (~692 revs; tol 1.5 %) |

`compare.py` recomputes the engine reference numbers live, so they can never go stale.

## Getting STK (the trial)

* STK is **Windows desktop** software — install it on the Windows host, *not* WSL.
* Request the **free trial** at ansys.com → STK → *Free Trial* (typically 30 days,
  Pro-level, **includes Astrogator**; a node-locked license is emailed).
* The perpetual **"STK Free"** tier is *not* sufficient — it has no Astrogator, and both
  checks need it.
* Trial terms change occasionally; confirm Astrogator is included before planning a run.

## Path A — scripted (preferred)

On the **Windows host**, with STK 12.x installed and licensed:

```bat
:: 1. install the STK Python API wheel that ships with the install
pip install "C:\Program Files\AGI\STK 12\bin\AgPythonAPI\agi.stk12-<ver>-py3-none-any.whl"

:: 2. from a clone of this repo (the repo is reachable from Windows at \\wsl$\... too)
cd audit\stk
python run_stk_audit.py
```

The script opens STK, builds both Mission Control Sequences, runs them, and writes
`out/stk_results.json`. Then, from either Windows or WSL:

```bash
python audit/stk/compare.py       # PASS/FAIL vs fermi_sim
```

The STK object-model property names in `run_stk_audit.py` follow the STK 12 Python API
samples; if your STK version renames one, the script fails loudly at that exact step and
tells you to fall back to Path B for that setting. **This package is prepared blind (no STK
license on this machine yet) — expect possibly one or two such touch-ups on first run.**

## Path B — manual GUI walkthrough

Everything can be done by hand in the STK GUI, then typed into the JSON.

**Common setup** — new scenario; insert a Satellite; set its propagator to **Astrogator**.
In the MCS, edit the **Initial State** segment: Cartesian, Earth inertial,
`X = 6771 km, Y = Z = 0, Vx = 0, Vy = 7.672685 km/s (circular), Vz = 0`;
Spacecraft parameters: Dry Mass 999 kg, Fuel Mass 1 kg.

**Check 1** — add a **Maneuver (Impulsive)** segment: Attitude Control = *Thrust Vector*,
axes *Satellite VNC(Earth)*, ΔV = `(14.633297, 0, 0) km/s` (X = along velocity). On the
segment's *Results* tab add **Keplerian Elems → C3_Energy**. Run the MCS; read the post-burn
C3 from the segment results (or the summary report).

**Check 2** — Component Browser → *Engine Models* → duplicate **Constant Thrust and Isp** →
set Thrust = 0.5 N, Isp = 1e7 s. Add a **Maneuver (Finite)** segment: Attitude Control =
*Thrust Vector*, axes *Satellite VNC(Earth)*, thrust vector `(1,0,0)`; Engine = your new
model; Propagator = **Earth Point Mass** (stock); Stopping conditions: *UserSelect* →
calc object **C3_Energy**, trip **0**, direction increasing (plus a *Duration* backstop of
3e7 s). Results tab: add **Time → Duration**. Run (it's ~692 revolutions — give it time);
read the maneuver Duration.

**Record** the two numbers in `out/stk_results.json`:

```json
{
  "check1_c3_km2s2": 379.8154,
  "check2_escape_s": 1.4266e7
}
```

then run `python audit/stk/compare.py`.

## Notes

* **Earth GM**: STK's Earth μ (≈398600.4415 km³/s²) differs from the engine's 398600.4418
  by <1 ppm — orders of magnitude inside the tolerances.
* **Why C3 as the stop condition works here (unlike GMAT)**: Astrogator stops on a calc-object
  crossing without converting the state to Keplerian elements, so the parabolic singularity
  that forced the GMAT audit to log Cartesian states and find the energy zero-crossing in
  post-processing doesn't bite. If your STK build disagrees, fall back to a Duration sweep
  and bisect on the C3 sign, or export an ephemeris and post-process as the GMAT audit does.
* Once results exist, commit `out/stk_results.json` (+ a `comparison_result.txt` capture of
  `compare.py`'s output) the way `audit/gmat/out/` is committed, and add `stk/` to the
  page's repository-structure list.

## Files

```
run_stk_audit.py   Windows driver: builds + runs both checks in Astrogator via the STK
                   Python API, writes out/stk_results.json
compare.py         parses out/stk_results.json, computes fermi_sim refs live, PASS/FAIL
out/               results land here (committed once a run exists)
```
