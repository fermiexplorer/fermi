# 13 — Three.js chase cam (replace per-frame Plotly gl3d)

> **STATUS: SPEC — awaiting confirmation before coding.**

## Problem (diagnosed)
The chase cam (`follow3d`) is drawn with **Plotly `scatter3d`**, rebuilt via `Plotly.react()` on ~10
traces every 40 ms (`setInterval`). Plotly is a charting lib, not a real-time 3D engine: per-frame full
scene rebuilds + a flaky relayout-driven camera (the code already has a rAF workaround comment for it)
→ slow, jerky, popping/flicker artifacts. The scene is tiny (a few polylines + ~6 markers + grid), so
the bottleneck is Plotly overhead, not geometry.

## Approach — Three.js, renderer-only swap
Keep ALL physics/geometry (`craftState`, `buildTraj`, disk/escape point generation, the framing/zoom
logic, the orbit-plane basis). Replace ONLY the drawing + camera of the `follow3d` panel:

- **One shared `THREE.WebGLRenderer`** (guard against the browser WebGL-context cap; the other panels
  migrate later onto the same renderer via viewport/scissor).
- `THREE.PerspectiveCamera`; the chase transform is just
  `cam.position = center − v̂·dist; cam.up = n; cam.lookAt(center)` — this DELETES the hand-rolled
  `autoEye`/`tc` eye+up sphere-interpolation (~30 lines). The top-down→chase transition becomes a lerp
  of the *look-from* direction between the disk normal and −v̂.
- Geometry as reusable objects, updated in place (not recreated): `THREE.Line` (flown arc, AC track,
  grid via `GridHelper`), `THREE.Points`/small spheres (Sun/Earth/probe/AC/intercept), and the
  Earth-escape disk/ring/spiral. Update `.geometry.setPositions`/positions per frame — no rebuild.
- **`requestAnimationFrame` loop** (not `setInterval(40)`); render only when playing or dirty.
- Pixel scaling: world units are AU; scale into a view cube of half-width `H` (the existing zoom).
- Keep **Plotly for the 2D charts** and the other panels (for now).

## Code-simplicity goals (explicit)
- Net LOC for the chase cam should DROP vs today. A thin helper module: `chase3dInit()` (once) +
  `chase3dDraw(c, st)` (per frame, ~60–80 lines). No projection/clip/depth math (Three.js does it).
- No per-frame allocation: reuse geometries/materials; mutate attributes.

## First cut vs the Earth-escape disk
The elaborate log-time geocentric disk→chase transition (SOI disk, spiral, tilt-to-contain-escape) is
where most past churn lived. Two options for THIS first cut (see decision below):
- **(A) Port it faithfully** — same geometry, re-rendered in Three.js (more code, preserves behavior).
- **(B) Simplify** — a clean chase cam: camera behind the probe along velocity for the whole Play;
  represent Earth escape as a small marker + the real escape arc (drop the disk/spiral theatrics).
  Less code, fewer artifacts, aligns with the simplicity goal; loses the "Saturn-disk" visual.

## Coexistence / rollout
- Implement behind a flag (`?r3=1` or a checkbox) so Three.js and Plotly chase cams can be A/B'd.
- Verify, then flip the default and remove the Plotly `follow3d` path.

## Verification (BEFORE deploy — chase-cam history demands it)
`tmp/ro/test_chase3d.py` (Playwright): play the animation; assert
- **fps** ≥ ~55 (rAF) vs the current ~25 target; no long frames.
- **camera physics**: at sampled times the view-from direction is ≈ −v̂ (chase), smooth (no jumps);
  asymptote ∥ aim at every zoom.
- **no artifacts**: no NaN positions, no ghost/second curve, markers persist (no popping).
- no JS/WebGL console errors; one WebGL context only.
- Screenshots at 3 zooms × 3 times, compared to the Plotly version.

## Push/deploy
Build NN, index.html (+ Three.js CDN, pinned), inline deploy. Engine/physics.js unchanged → parity
untouched; ui_sliders + native-default guard still green.

## Decision needed
For the first cut: **(A) faithfully port the Earth-escape disk transition, or (B) simplify to a clean
behind-the-probe chase** (smaller code, drops the disk theatrics)?
