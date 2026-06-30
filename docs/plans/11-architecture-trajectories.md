# 11 — True-architecture trajectory rendering (Solar-Oberth sundiver + Jupiter flyby)

> **STATUS: SPEC / IN PROGRESS.** Approved approach (chat): render the *real* trajectory for each
> TRAJECTORY ARCH option instead of always drawing the direct outward escape.

## Problem (diagnosed)
`buildTraj(vhat, vinfKmS)` takes no architecture argument — it always integrates the **direct**
heliocentric escape (1 AU → 1/r²-faded tangential thrust → coast to v∞). So the 3D/chase-cam views
draw a plain outward spiral for *all three* architectures. The Δv math in `compute()` is correct per
architecture, but the **visualization ignores `ga`**. For Solar-Oberth this is qualitatively wrong:
a sundiver first dives *sunward* to a close perihelion, burns there, then whips outward — the chase
cam should look toward the Sun during the dive, then flip outward after the burn. Today it only ever
shows the outward leg.

## Design — `buildTraj(vhat, vinfKmS, ga, rpRsun)`
Keep the direct path byte-for-byte; branch on `ga`. All integration in the existing 2D heliocentric
frame (MU=4π², AU/yr), then rotate so the final escape asymptote → `vhat` (unchanged embed step).

### `ga==='direct'` (unchanged)
Current code path exactly. Regression: identical output for the same (vhat, vinf).

### `ga==='oberth'` — sundiver
1. **Dive:** start at 1 AU on an ellipse whose perihelion = `rp` (slider, R☉ → AU). Initialise at
   aphelion (r=1 AU) with the ellipse's aphelion speed `v_a = sqrt(MU·(2/r_a − 1/a))`,
   `a = (r_a + r_p)/2`, **no thrust** (a coast/assist-set dive). Integrate to perihelion.
2. **Burn:** at perihelion apply a prograde impulse so specific energy → `½v∞²` (i.e. set speed to
   `sqrt(v_p² + v∞²_escape)` for the hyperbola). This is the Oberth burn the KPI already sizes.
3. **Escape:** integrate the hyperbola outward (no thrust) until r>24 AU; that asymptote is `vhat`.
- Camera/`craftState`: the probe distance must follow dive (1→rp) **then** climb (rp→rLast→Inorm).
  The log-time phase clock currently is earth/sun/cruise; the sundiver needs the "sun" phase to first
  decrease then increase. Spec: replace the monotone `dist` in the Oberth case with a dive-then-climb
  profile keyed off the same phase fraction.

### `ga==='jupiter'` — flyby bend
1. Integrate the direct faded-thrust escape (as now) but **stop at Jupiter's radius** (5.2 AU).
2. Apply a velocity-direction **bend** of the flyby (turn angle from `jupiterGain`/the hyperbolic
   deflection at the chosen approach), preserving speed, rotating the velocity toward `vhat`.
3. Continue the coast to v∞. The asymptote → `vhat` (so the post-flyby leg aims at AC).

## Verification (BEFORE any deploy — non-negotiable, per the chase-cam history)
Write `tmp/ro/test_arch_traj.py` (Playwright) that, for `ga ∈ {direct, oberth, jupiter}`, samples the
rendered path + camera at multiple times, angles, and zoom levels and asserts:
- **Oberth:** probe radius is **non-monotone** — strictly decreases to ≈`rp` then increases (the dive);
  min radius ≈ `rp` (slider) within tolerance; velocity reverses sense through perihelion; final
  asymptote ‖ `vhat` (cos≈1) at every zoom; no second/ghost curve; C¹-continuous (no jumps).
- **Jupiter:** a single bend near 5.2 AU; speed continuous across the bend; final asymptote ‖ `vhat`.
- **Direct:** byte-identical to pre-change (regression guard).
- All three: tangent-by-construction at the frame edge regardless of zoom (the property the user
  demanded earlier); analyse frame-by-frame, not just endpoints.
Then `ui_sliders` (no JS errors), parity (unchanged — viz only), and a screenshot per architecture.

## Open spec questions (confirm before coding the camera)
1. In **log-time** the dive happens inside the "sun-escape" third — render the dive+burn+escape all
   within that third (dist dips to `rp` then climbs)? (Proposed: yes.)
2. Show a small **Sun-proximity heat/perihelion marker** at the burn point for Oberth? (Proposed:
   minimal — a labelled perihelion dot; no new thermal modelling.)
3. Jupiter: draw a **Jupiter marker** at the flyby point? (Proposed: yes, a labelled dot at 5.2 AU.)

## Push/deploy
Build NN (viz-only, inline deploy to both Pages clones). Engine/physics.js unchanged → parity
untouched; the changes are confined to `buildTraj`/`craftState`/the chase-cam in index.html.
