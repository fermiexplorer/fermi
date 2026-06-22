# 10 — The pure-electric closure: nuclear-electric + solar-Oberth depth

> **STATUS (builds 62–64): IMPLEMENTED + VERIFIED + DEPLOYED.** Follows
> [09-conservative-sep-gate.md](09-conservative-sep-gate.md), which proved pure SOLAR-electric is
> power-limited and left open *which* electric path closes. Answer: **nuclear-electric (constant
> power)**. Shipped: the `fade_exp` power law (engine + physics.js, parity 19/19), the power-source-
> aware feasibility gate, the conservative pure-EP departure Δv, the reactor power option, the
> solar-Oberth in-depth methodology, the chemical-kick scale note, and a compliance scrub of the
> non-public benchmarking-source wording. Audits: parity 19/19, audit_departure 22/22 (incl.
> independent Euler-Cromer NEP closure), run_audits 55/55, ui_sliders 63/63, pytest 8/8.

Goal: answer "find a closure path with EP only" honestly and conservatively, then document the
trade against the other closing architectures.

## The finding
- **Pure solar-electric never closes.** With thrust faded 1/r² (`sep_achievable_vinf(..., fade_exp=2)`)
  the achievable v∞ saturates below the 23.4 km/s floor at any power (bigger array → more mass, same
  saturation). 5 kW → 0, 10 kW → 0, 20 kW → 14.4 km/s.
- **Nuclear-electric closes.** Constant power (`fade_exp=0`) keeps the spiral thrusting all the way
  out. Achievable v∞ rises with power (1 kW → 18, 3 kW → 23, 5 kW → 25 km/s) but the reactor mass
  rises too, so the closure is a narrow corner: **~5 kW reactor @ ~40 W/kg + gridded ion (Isp ~3000 s)
  → ~24.8 km/s, ~64% xenon, +64 kg dry-bus margin.** Needs BOTH nuclear power AND high Isp.
- **An RTG does not help** — right kind of power (constant) but ≤1 kW (→ 15–18 km/s) and ~5 W/kg
  (a 5 kW RTG ≈ 1000 kg). Need a multi-kW reactor.

## Implementation (engine-first)
1. `fermi_sim/departure.sep_achievable_vinf` gains `fade_exp` (2 = solar 1/r², 0 = constant nuclear);
   both the deriv thrust and the burn-rate use `(r0/r)**fade_exp`. Mirrored to
   `web/physics.sepAchievableVinf` (cache key includes fadeExp); JS↔Py parity ref for fade_exp=0.
2. `index.html compute()`: `fadeExp = (pwr==='solar') ? 2 : 0`; the power gate is the **decisive,
   first-reported** feasibility test for `ga==='direct'`. Conservative pure-EP departure Δv = the
   tilt-aware spiral + a constant ~5 km/s heliocentric-spiral offset (no Earth-velocity borrow);
   the ~73 kyr fuel optimum is preserved (constant offset doesn't move the optimum).
3. Power UI: "Nuclear-electric (reactor) — constant power"; specific-power slider 2–50 W/kg (def 40).
   Verdict/KPI/infeasibility text made power-source-aware.
4. `run_analysis.py` §7 conservative power gate + §8 conservative verdict; `docs/REPORT.md` rewritten
   to the conservative conclusion.

## Solar-Oberth, in depth (build 64, methodology §5b)
A ~1.4 km/s burn at 10 R☉ yields the full 24 km/s (~4.3× Oberth leverage vs buying it at 1 AU), BUT:
(1) the burn must be **chemical** — ion is too slow for the hours-long perihelion pass (~58 days for
1.4 km/s); (2) ~1830 K demands a **Parker-class heat shield** (deeper = hotter, beyond shields);
(3) reaching ~10 R☉ needs a **Jupiter/Venus assist tour** to shed Earth's angular momentum. It
sidesteps the power wall rather than solving it.

## Chemical kick scale note (build 64)
~14 km/s impulsive from LEO does the whole job. A ~3.7 km/s kick does NOT — it barely clears Earth's
SOI (helio v∞ ≈ 0); v∞ adds in quadrature, so a useful kick is ~10+ km/s. No cheap small-kick shortcut.

## Compliance (build 63)
CLAUDE.md forbids naming the customer/bus partner or any non-public benchmarking source in shipped
artifacts. Build 61 introduced wording that referenced a non-public benchmarking source; build 63
removed every occurrence from the live page, the engine docstring, plan 09, and the frozen public
builds b61/b62, replacing it with neutral "1/r² power-fade analysis" phrasing. No partner name ever
appeared anywhere — only the generic reference, now gone.

## Verification
- `node audit/calcs/audit_webjs.mjs` — parity 19/19 (incl. fade_exp=0 NEP ref).
- `.venv/bin/python audit/calcs/audit_departure.py` — 22/22 (independent Euler-Cromer NEP closure:
  25.5 km/s vs solar 0.0).
- `.venv/bin/python audit/calcs/run_audits.py` — 55/55.
- `.venv/bin/python audit/calcs/ui_sliders.py` — 63/63 (EP-only closure checks; no JS errors).
- `.venv/bin/pytest` — 8/8.  `.venv/bin/python run_analysis.py` — conservative §7/§8 print.
- Screenshots: `/tmp/screenshots/ss-nep-closure.png` (feasible nuclear design),
  `ss-oberth-depth.png` (§5b table).

## Push/deploy (done)
- Source `fermi` branch `codex/v4-prompt10-audit`: build 62 `467f65f`, 63 `080117b`, 64 `150cf8e`.
- Pages clones (inlined, frozen b62/b63/b64 + latest index.html): `fermiexplorer.github.io` and
  `app-c39aacb1d537`, both pushed to `main`. Live build = 64.
