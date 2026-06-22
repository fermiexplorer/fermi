# 05 — Replace the 2D spiral inset with a growing 3D Earth-escape disk

## Motivation

The 2D Earth-escape spiral inset (Plan 03) reads as a dense green blob and lives in a
separate panel disconnected from the trajectory. User: "that Earth-escape spiral is
weird. Delete it." Replace it with a **3D disk of increasing radius around Earth** drawn
**inside the chase cam**, from which the escape trajectory continues — with a **smooth,
continuous zoom** from Earth scale out to Sun scale (no hard jump), the camera zooming
out as the disk grows.

## Concept (user-directed)

- During the **earth phase**, the chase cam is zoomed to geocentric scale and **looks
  straight down (top-down, 90°)** on the ecliptic: **Earth = a blue dot** (a 2D circle
  marker — deliberately simple) at center, with an **in-place green spiral** (≈28
  representative loops, Archimedean) over a faint **filled green disk**, both growing from
  the parking orbit (r_p) out to the sphere of influence (SOI ≈ 145 R⊕). Top-down the
  spiral reads circular (like the old inset, but correct); the disk = the orbit-raising
  envelope swept by the ~hundreds of revolutions.
- As the probe **escapes**, the camera **rotates from top-down to a true chase cam**
  (behind the escape-velocity, tilted) — so the spiral/disk tilts into an **ellipse** — and
  simultaneously **zooms out continuously as the disk grows** (frame half-width tracks the
  disk radius), smoothly through SOI → AU → tens of AU. No phase branch in the framing →
  no scale jump. The green disk/spiral **becomes insignificant** at AU scale, and the
  **escape trajectory curve** (the existing heliocentric escape arc) is drawn emanating
  from it. The camera-rotate + zoom-out are both driven by `distFromEarth` so they are
  continuous and tied to real motion.
- Rev count + departure time (`earth_escape_revs`, design-responsive) stay as the panel's
  honest labels in the title.

## Implementation (index.html only — no physics/engine change)

### Remove
- `drawEarthSpiral()` function and its call in `drawViz()`.
- `<div class="espiralrow">` … `#earthSpiral` chart markup (keep the caption text — see
  Relocate). CSS: `.espiralrow`, `#earthSpiral`, (keep `.espiralcap` for the relocated note).

### Add geometry helpers (near the trajectory drawing code)
- `diskMesh(center, R, n, color, opacity)` → a Plotly `mesh3d` filled disk (fan
  triangulation) in the z = center.z plane.
- `spiralPts(center, r0, r1, turns, perTurn)` → Archimedean spiral polyline in that plane.
- `smooth01(t)` → smoothstep helper.

**Spiral → disk transition:** early in the earth phase draw a **few-turn** bright spiral
(`turns = 2 + prog·6`) over a near-transparent disk; as `prog` rises, ramp the **disk
opacity** up (`0.26·smooth01((prog−0.25)/0.5)`) so the loops visually merge into a filled
disk. Both fade by `(1−bSun)` after escape so they shrink to insignificance.

### Modify `drawFollow3d(c, st)`
1. `Epos = st.arc[0]` (Earth's heliocentric position = escape-arc start).
2. `prog` = earth-phase orbit-raising fraction (phaseOf earth `f`, log-accelerated when
   `logTimeMode()`); `diskRE = rpRE + prog*(SOI_RE − rpRE)`; `diskAU = diskRE*R_EARTH_AU`.
3. **Continuous framing** — replace the `flown.concat([[0,0,0]])` box with points that grow
   smoothly: flown arc + probe + **disk rim** (radius `diskAU` around `Epos`, so the frame
   floor = the disk) + a **smooth Sun anchor** `lerp(Epos, origin, smooth01(distFromEarth/1AU))`
   (Sun enters frame only as the probe leaves Earth — no jump). `ctr`/`H` from this box as today.
4. **Traces:** green `diskMesh(Epos, diskAU, 64, '#3fb950', 0.26*(1−bSun))` (fades as we zoom
   out) + bright orbit-edge ring + **blue Earth dot** at `Epos` + probe marker (on the disk
   rim during the earth phase: `Epos + diskAU·(cosφ,sinφ,0)`, φ rotating; on the arc after).
   The existing green **flown arc** is the escape trajectory and already starts at `Epos`.
5. Title: earth phase → `Earth-escape: orbit-raising · ≈N revolutions · t yr`; else the
   existing `solar-escape spiral` / `interstellar cruise` tag.
6. Camera eye unchanged (`autoEye` from the escape-direction tangent at the arc start is
   already stable during the earth phase → continuous into the chase). Tilt → disk reads
   as an ellipse.

### Relocate the methodology text
Move the "many-revolution Earth departure" paragraph to a **full-width note after the 3D
graphs / burn timeline** (where the inset row was), without the chart. Keep wording; adjust
the final clause from "plays here at its own scale" → the chase cam zooms into it at the
start of the journey.

## Verification
1. `tmp/ro/test_diskcam.py` (replaces test_phaseclock inset asserts): at `animU` in each
   third — earth: chase-cam has a `mesh3d` disk trace with rim radius growing between two
   earth-phase samples, frame half-width `H` grows too (zoom-out), Earth dot present;
   sun/ac: disk faded (opacity→0) / insignificant, escape arc drawn, `H` keeps growing
   monotonically across the earth→sun boundary (smoothness: no >3× step). No JS errors.
2. `ui_sliders.py` → 53/53 (or adjust any earthSpiral-referencing check).
3. `pytest` 8/8, parity `audit_webjs.mjs` 13/13 (engine untouched).
4. Screenshot at three Play positions (mid-earth, escape handoff, cruise) for visual review
   BEFORE deploy.

## Push / deploy
1. Commit index.html + plan with `git commit -F tmp/rw/commit-msg.txt`; push `origin HEAD:main`.
2. Bump `BUILD 48 → 49`, h1 "build 48" → "build 49".
3. `tmp/rw/deploy_build.py` BUILD=49 + new SHA; run (inlines physics.js).
4. Commit + push both Pages clones; poll `https://fermiexplorer.github.io` for "build 49".
