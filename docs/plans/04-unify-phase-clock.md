# 04 — Unify the animation on one phase clock

## Problem

`animU ∈ [0,1]` drives the Play/scrub animation, but **three independent clocks**
consume it and disagree, so the views desync (reported: "burn graph shows Earth
escape while chase cam shows sun escape"; "I'm not seeing revolutions around Earth"):

1. **`phaseOf(u)`** (index.html:990) — splits Play into equal thirds
   `earth` (0–⅓) / `sun` (⅓–⅔) / `ac` (⅔–1). The view-selector radios auto-switch
   on these thirds (line 999); the burn timeline is segmented Earth-escape / Sun-escape
   / coast.
2. **`craftState()`** (line 1031) — ignores `phaseOf`; runs a *continuous* heliocentric
   distance clock `dist = Inorm^animU` (log) / linear. The burn "▲ now" marker reads
   `craftState().es` (line 1380), so it tracks THIS clock, not the segments.
3. **`drawEarthSpiral` revProg** (line 1404) — maps `animU` directly (log-accelerated)
   to the geocentric 0→961 revolutions.

At e.g. `animU≈0.2` (log): inset = ~3 % Earth-escape · chase cam = Sun-escape spiral
(`dist≈5 AU`) · burn now-marker ≈135 yr (coast). All three disagree → the Earth
revolutions never line up with anything and look absent.

Root cause: the system was *designed* around `phaseOf`'s three stages (radios + burn
segments honor it), but `craftState` and the inset drifted onto their own clocks.

## Decision

**Unify on `phaseOf`** (user-selected). One phase model drives every view. Each of the
three phases owns an equal third of Play time (so each is watchable); the log/linear
toggle controls how distance is spread *within* the heliocentric phases and the burn
axis type.

- **`earth` third (0–⅓):** geocentric Earth escape. Heliocentric `dist` HOLDS at
  1 AU (the craft is still bound to Earth — it must not fly outward yet). The probe
  sits at the start of the heliocentric arc. The inset winds revProg 0→1. The burn
  "now" marker walks the Earth-escape segment.
- **`sun` third (⅓–⅔):** heliocentric spiral-out to v∞. `dist` sweeps 1 AU → end of
  the escape arc (`tj.rLast ≈ 24 AU`). Inset shows "escaped → heliocentric".
- **`ac` third (⅔–1):** interstellar cruise. `dist` sweeps `tj.rLast` → `Inorm`.

## Changes (index.html only — no physics/engine change)

1. **`craftState()` → phase-aware.** Replace the `dist = Inorm^animU` block with a
   `phaseOf(animU)`-driven piecewise map:
   - `earth`: `dist = RDEP` (1 AU, constant).
   - `sun`: `dist` interpolated 1 AU → `rLast` (log-spaced within the phase when
     `logTimeMode()`, linear otherwise — keeps the "early AU spread out" feel).
   - `ac`: `dist` interpolated `rLast` → `Inorm` (same log/linear within-phase rule).
   - `rLast` comes from `buildTraj(vhat, vinfKmS).rLast` (already computed).
   - `es` (elapsed yr, for the tlabel) derived from the unified `elapsedYrFromU`.

2. **`elapsedYrFromU(u)` → align to `burnPhases`** so the burn "now" marker tracks the
   drawn segments exactly:
   - `earth`: `f * p.tEarth`
   - `sun`: `p.tEarth + f*(p.tBurn − p.tEarth)`
   - `ac`: `p.tBurn + f*(p.arrival − p.tBurn)`
   (replaces the hardcoded `f*1.2 / f*6 / f*arrival`).

3. **Burn now-marker** (line 1380): `now = elapsedYrFromU(animU)` instead of
   `craftState().es/YEAR`. Now coherent with the segments.

4. **`drawEarthSpiral` revProg** (line 1404): drive from the phase, not raw animU:
   - `earth` stage → `revProg = f` (log-accelerated *within* the third when
     `logTimeMode()`, as today, so the slow high-altitude end compresses);
   - `sun`/`ac` → `revProg = 1` (escaped; inset shows the "escaped → heliocentric"
     annotation and the full bright spiral).

5. **`timeToU(tYr)`** (line 1550): invert the new piecewise map — find which burn
   segment `tYr` lands in (`earth`:0–tEarth, `sun`:tEarth–tBurn, `ac`:tBurn–arrival),
   then `animU = stageStartU(stage) + localFrac/3` (log-invert within phase when log).
   Keeps click-to-scrub on the burn timeline working.

6. **Loop count:** leave `ESPIRAL_LOOPS=48`. The screenshot confirms the revolutions
   ARE drawn distinctly once the inset is the only thing on the Earth clock; the
   problem was sync, not density. (If still too dense after sync, drop to ~24 in a
   follow-up — not part of this change.)

## Out of scope

- No change to `fermi_sim/` or `web/physics.js` — this is pure UI animation wiring,
  so the parity audit and engine audits are unaffected.
- No change to the physics of `earth_escape_revs` / `lowthrustDepartureDv`.

## Verification

1. `.venv/bin/python audit/calcs/ui_sliders.py` → 53/53, no JS console errors.
2. `.venv/bin/python tmp/ro/test_phaseclock.py` (new): assert at `animU` in each third —
   - earth third: `craftState().dist ≈ 1 AU`, inset revProg ∈ (0,1), burn now-marker
     ≤ tEarth, chase-cam probe near arc start;
   - sun third: `dist` ∈ (1, rLast], inset escaped, now-marker ∈ (tEarth, tBurn];
   - ac third: `dist` ∈ (rLast, Inorm], now-marker ∈ (tBurn, arrival].
   - NO JS errors.
3. Screenshot at mid-earth third: inset winding + chase cam holding at ~1 AU +
   burn marker in Earth-escape segment (visual coherence).
4. `.venv/bin/python -m pytest tests -q` → 8/8 (regression guard; engine untouched).
5. Parity unchanged: `node audit/calcs/audit_webjs.mjs` → 13/13 (engine untouched).

## Push / deploy

1. Branch is already `codex/v4-prompt10-audit`. Commit index.html (+ plan + test) with
   `git commit -F tmp/rw/commit-msg.txt`; `git push origin HEAD:main`.
2. Bump `BUILD 47 → 48` and h1 "build 47" → "build 48" in index.html (same commit).
3. `tmp/rw/deploy_build.py`: set `BUILD=48`, new SHA; run it (inlines physics.js).
4. Commit + push both Pages clones (`../tmp/fermi-pages-2`, `../tmp/fermi-root`)
   with `git commit -F ../../fermi/tmp/rw/dmsg.txt`.
5. Poll `https://fermiexplorer.github.io` for "build 48".
