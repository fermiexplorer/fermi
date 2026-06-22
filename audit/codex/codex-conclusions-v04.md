# Codex Conclusions v04 - prompt 10 rerun

Date: 2026-06-21

Scope: rerun the audit against the new prompt 10 in `audit/AUDIT_PROMPTS.md`,
focused on the 58 kyr minimum-speed intercept and the "modest xenon" framing.
The independent calculation script for this round is
`audit/codex/v4_prompt10_checks.py`. It does not import `fermi_sim`.

## Bottom line

No new physics blocker was found. The current calculator and copy correctly
separate the minimum-speed arrival near 58 kyr from the minimum-departure-delta-v
arrival near 72.8 kyr. The "modest xenon" claim is defensible only when stated
as "modest for this interstellar precursor architecture" and sized on the
realistic low-thrust SEP budget, not on the impulsive Oberth floor.

The best current sizing statement is:

- 58,138 yr minimum-speed intercept: 23.2719 km/s heliocentric v_infinity,
  tilted -9.99 deg, 14.633 km/s impulsive LEO floor.
- 58,000 yr slider value: 23.2720 km/s, tilted -10.08 deg, 14.651 km/s
  impulsive LEO floor.
- Independent low-thrust spiral bound for the same 58 kyr target: 25.99 km/s.
- 20 km/s optimized-SEP sizing budget: 248.2 kg xenon on a 255 kg dry bus,
  49.3% propellant fraction, 503.2 kg wet.

## Independent vector check

At the exact tangential arrival, 58,138.323 yr:

| Term | x km/s | y km/s | z km/s | magnitude |
|---|---:|---:|---:|---:|
| A0 / T aim term | -8.374 | -14.205 | -15.160 | 22.400 km/s |
| V_ac lead term | -9.222 | +28.890 | +11.121 | 32.301 km/s |
| V_p = A0/T + V_ac | -17.597 | +14.684 | -4.039 | 23.2719 km/s |

The plane angle from this vector is -9.995 deg. The prompt's warning is
correct: the bare distance-over-time speed is only 22.4 km/s; Alpha Centauri's
own transverse motion is what sets the actual 23.27 km/s intercept velocity.

## Departure chain

For the exact 58,138 yr tangential intercept:

- heliocentric speed at 1 AU before solar escape: 48.123 km/s
- Earth orbital speed borrowed in-plane: 29.785 km/s
- Earth-relative hyperbolic excess: 19.489 km/s
- 400 km LEO circular speed: 7.673 km/s
- 400 km LEO escape speed: 10.851 km/s
- post-burn perigee speed: 22.306 km/s
- impulsive LEO delta-v floor: 14.633 km/s

At the round 58,000 yr value used by the page table, the independent result is
14.651 km/s, matching the displayed 14.65 km/s.

The separate `solve_ivp` low-thrust spiral simulation, run to the same
Earth-relative target energy at 5e-4 m/s^2 tangential acceleration, gives
25.987 km/s over 1.647 yr. That matches the prompt's 26.01 km/s bound closely
enough for this model.

## Propellant and mass closure

Rocket-equation masses for a 255 kg dry bus:

| Case | Delta-v | Isp | Propellant | Fraction | Wet mass |
|---|---:|---:|---:|---:|---:|
| 58 kyr impulsive floor | 14.633 km/s | 3000 s | 164.3 kg | 39.2% | 419.3 kg |
| min-delta-v impulsive floor | 13.875 km/s | 3000 s | 153.7 kg | 37.6% | 408.7 kg |
| design SEP budget | 20.000 km/s | 3000 s | 248.2 kg | 49.3% | 503.2 kg |
| 58 kyr spiral bound | 25.987 km/s | 3000 s | 361.8 kg | 58.7% | 616.8 kg |
| 58 kyr impulsive floor | 14.633 km/s | 4000 s | 115.3 kg | 31.1% | 370.3 kg |
| design SEP budget | 20.000 km/s | 4000 s | 169.6 kg | 39.9% | 424.6 kg |
| 58 kyr spiral bound | 25.987 km/s | 4000 s | 239.6 kg | 48.4% | 494.6 kg |

Default dry-mass closure at the 20 km/s, Isp 3000 s design point:

- silicon array: 18.37 m2, 55.1 kg
- thruster + PPU: 30.0 kg
- xenon tank at 8% of propellant: 19.9 kg
- array + engine + tank: 105.0 kg
- dry remainder for bus, payload, harness, structure, margin: 150.0 kg

Even the naive 58 kyr spiral-bound case leaves 140.9 kg of the 255 kg dry bus
after array, engine, and tank. This does not prove detailed mechanical design,
but it means the first-order dry-mass budget is not internally impossible.

## Framing verdict

"Long trip != large delta-v" is still valid. The 58 kyr intercept is set by
4.513 ly of target distance at a Voyager-class 23.27 km/s cruise speed. The
mass ratio stays near 2 at the 20 km/s design point because Isp 3000 s gives
v_e = 29.42 km/s, the same order as the required delta-v.

The possible communication trap is the word "modest":

- Honest: "~250 kg xenon, about half of a 500 kg wet vehicle, is modest for a
  direct interstellar precursor SEP architecture."
- Misleading: "the 58 kyr minimum-speed point only needs ~165 kg xenon" if that
  number is presented as the actual low-thrust sizing case. It is the impulsive
  floor, not the ion-spiral budget.

The current `index.html`, `README.md`, and `docs/REPORT.md` do not appear to
conflate the 58 kyr minimum-speed point with the 72.8 kyr minimum-delta-v point.
The page explicitly says the calculator sizes to the minimum-propellant optimum
near 73 kyr and that the 58 kyr aim costs more delta-v due to out-of-plane tilt.

## Residual risks

1. The largest open engineering risk remains the finite-burn low-thrust
   trajectory. The 20 km/s SEP number is a benchmark between a 14 km/s impulsive
   floor and a 26 km/s naive spiral bound, not a solved phased trajectory.
2. The departure model assumes best-case launch timing for the in-plane
   projection. A real calendar launch could add cost.
3. The 40-60% propellant fraction is plausible for one-stage EP storage, but
   detailed tank, feed, thermal, and structural design is still outside this
   first-order model.
4. The hardware defaults close mathematically, but array deployment, long
   storage, radiation, autonomy, communications, and 75 kyr survival remain
   outside scope.

## Verification run

Passed:

- `.venv/bin/python audit/codex/v4_prompt10_checks.py`
- `.venv/bin/python audit/calcs/run_audits.py` - 41/41
- `node audit/calcs/audit_webjs.mjs` - 10/10
- `.venv/bin/python audit/calcs/ui_sliders.py` - 51/51, run with Chromium
  outside the sandbox
- `.venv/bin/pytest tests` - 8/8

Did not pass in this environment:

- `.venv/bin/python audit/calcs/ui_playwright.py` launched Chromium outside the
  sandbox but timed out waiting for `#follow2d .plot-container`. The page uses
  the Plotly CDN, and the failure is consistent with the render audit not
  loading Plotly in this restricted environment. The pure calculator behavior
  was covered by `ui_sliders.py`; the full visual render should be rerun in an
  internet-enabled browser environment.

One broad `.venv/bin/pytest` invocation was intentionally not used as a result:
this repository contains many `tmp/ro` and `tmp/rw` diagnostic files named
`test_*.py`, so the tracked smoke suite should be run as `.venv/bin/pytest tests`
unless pytest collection is narrowed.
