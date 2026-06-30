# GMAT cross-validation

An **independent** check of the Fermi departure model against
[GMAT](https://gmat.gsfc.nasa.gov/) — NASA's General Mission Analysis Tool. GMAT is a
mature, flight-proven astrodynamics propagator developed completely separately from this
project, so agreement is a genuine cross-validation, not the engine checking itself
(see the project rule *"audits must stay independent"*).

GMAT reproduces two pillars of `fermi_sim/departure.py` to **better than 0.01 %**:

| Check | Quantity | `fermi_sim` | GMAT | Diff |
|-------|----------|-------------|------|------|
| 1 — impulsive (Oberth) departure | post-burn C3 | 379.8154 km²/s² | 379.8154 km²/s² | 2×10⁻⁶ % |
| 2 — low-thrust Earth-escape spiral | escape time | 1.42657×10⁷ s | 1.42656×10⁷ s | 0.007 % |

## What is checked

Shared config (identical in both `fermi_sim` and the GMAT scripts):

* circular orbit, **radius 6771 km** (= `fermi_sim` "400 km altitude", mean R⊕ = 6371 km)
* **Earth point-mass** gravity only, μ = 398600.4 km³/s² (= `fermi_sim` `MU_EARTH`); no
  J2, drag, SRP, third bodies
* mission: min-speed intercept @ 58,138 yr → v∞,Sun = 23.270 km/s, tilt −10°

**Check 1 — `scripts/01_impulsive_departure.script`** validates
`impulsive_dv_from_leo` / `v_inf_earth_required`. GMAT applies the Fermi-computed
departure Δv of 14.633297 km/s prograde at the circular orbit; the resulting hyperbolic
`C3Energy` must equal the required v∞,Earth² = 379.8154 km²/s². Pure Keplerian.

**Check 2 — `scripts/02_lowthrust_escape.script`** validates `spiral_escape_dv` /
`earth_escape_revs`. GMAT applies constant tangential (prograde) thrust from the circular
orbit and propagates ~692 revolutions to Earth escape. `fermi_sim` integrates a *constant*
acceleration of 5×10⁻⁴ m/s²; GMAT reproduces that with 0.5 N on 1000 kg and a huge Isp
(10⁷ s), so propellant draw (~0.07 kg) leaves the acceleration essentially constant.
"Escape" is the first crossing of specific orbital energy ½v² − μ/r = 0 — the exact
condition `fermi_sim` uses. `compare.py` finds that crossing from GMAT's logged Cartesian
state.

> **Why log the state instead of stopping on `C3 = 0`?** GMAT computes C3 from the
> semi-major axis a (C3 = −μ/a), which is singular exactly at the parabolic escape point
> (a → ∞). So script 2 logs the Cartesian state every 20000 s and `compare.py` computes
> the energy crossing directly — robust and identical to the engine's definition.

## Run it

```bash
cd audit/gmat
./install_gmat.sh      # downloads GMAT R2020a (Linux/WSL; ~338 MB, git-ignored)
./run_gmat.sh          # runs both scripts headless, then compare.py
```

Expected tail:

```
RESULT: ALL CHECKS PASS -- GMAT confirms the Fermi engine
```

`compare.py` computes the `fermi_sim` reference numbers live (they can never go stale) and
needs the project's Python deps (numpy/scipy); `run_gmat.sh` auto-uses `.venv` if present.

## Platform notes

GMAT **R2020a** is the last NASA release with a Linux binary (the Ubuntu x64 build also
runs under WSL), so that is what `install_gmat.sh` fetches. The scripts are plain GMAT and
also run on current **R2026a** for Windows/macOS:

* Windows: `gmat-win-R2026a.zip` — open each `scripts/*.script` in the GUI and **Run**, or
  point `GMAT_BIN` at the folder with `GmatConsole.exe` and use `run_gmat.sh`.
* macOS: `gmat-mac-x64-R2026a-signed.dmg` — same.

Then `python3 compare.py`.

## Files

```
scripts/01_impulsive_departure.script   INPUT: GMAT check 1 (impulsive departure)
scripts/02_lowthrust_escape.script      INPUT: GMAT check 2 (low-thrust escape spiral)
install_gmat.sh                         download + extract GMAT (Linux/WSL)
run_gmat.sh                             run both scripts headless + compare
compare.py                              comparison script: GMAT output vs fermi_sim, PASS/FAIL
out/01_impulsive.txt                    OUTPUT: raw GMAT report, check 1   (committed for inspection)
out/02_lowthrust.txt                    OUTPUT: raw GMAT state log, check 2 (committed for inspection)
out/comparison_result.txt              OUTPUT: the engine-vs-GMAT comparison (committed for inspection)
out/README.md                           describes the output files
```
