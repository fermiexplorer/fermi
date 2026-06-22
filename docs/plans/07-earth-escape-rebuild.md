# 07 — Earth-escape visualization: complete spec (agree BEFORE coding)

> **STATUS (build 56): IMPLEMENTED + VERIFIED.** Disk = SOI (your choice, 0.0124 AU dia).
> The escape is the REAL heliocentric arc translated by one SOI so it roots on the disk edge
> tangentially; the shift is negligible at AU scale, so it becomes the cruise arc seamlessly —
> one curve, no second trajectory, no shape morph at the hand-off. `tmp/ro/test_escape.py`
> passes all 27 (time × angle × zoom) cases: one curve · on edge · tangent · ends at probe ·
> no loop. Frame sweep eyeballed.


Purpose: stop iterating on broken trajectories. Define the exact geometry, the single-curve
rule, the camera, the time mapping, and the test, get sign-off, THEN implement once.

## A. The disk diameter (OPEN — needs your decision)

"Escape from Earth" means reaching the orbit where Earth's gravity hands off to the Sun.
The standard physical boundaries (computed from μ⊕/μ☉, at 1 AU):

| Boundary | radius | **diameter** | in Earth radii |
|---|---|---|---|
| Sphere of influence  r = a·(μ⊕/μ☉)^(2/5) | 9.25×10⁵ km | **0.0124 AU** | 145 R⊕ |
| Hill sphere  r = a·(μ⊕/3μ☉)^(1/3)         | 1.50×10⁶ km | **0.020 AU**  | 235 R⊕ |

There is **no standard Earth-influence boundary at ~0.1 AU** (that's ~7500 R⊕, ~⅒ of the
way to the Sun). So options:
1. **SOI = 0.0124 AU** (physically exact "escape" boundary).
2. **Hill = 0.020 AU** (the gravitational-capture boundary; a bit larger).
3. **A deliberately enlarged schematic disk (e.g. 0.1 AU)** — not physical, chosen purely
   so the disk reads big in the view. (If this is what you want, I'll label it as schematic,
   not "to scale".)

→ Tell me which. I'll compute it exactly in the engine either way.

## B. One trajectory, never two (the bug in build 55)

Build 55 cross-faded the geocentric escape curve AND the heliocentric cruise arc → two
curves on screen. Rule going forward: **exactly one green path is drawn at every frame.**

- It is ONE continuous curve: orbit-raising spiral (in the disk) → leaves the disk edge
  **tangentially** → bends to and **ends exactly at the heliocentric probe point p** → the
  cruise arc continues from p. Because the escape ends at p, the cruise arc starts where the
  escape ended — no second curve, no jump.
- The heliocentric arc is hidden until the escape curve has reached p (no overlap).

## C. Tangency (must hold at every zoom)

The escape leaves the disk edge ⟂ to the radius. Guaranteed by construction: pick the exit
point so the orbit's tangent there points toward p, then a Bézier with its first control
point along that tangent → initial direction ⟂ radius. Scales with the rendered disk radius,
so it's tangent at the edge at any zoom.

## D. Camera & time

- Camera: top-down on the dawn-dusk disk (face-on) during orbit-raising; rotates to the chase
  and zooms out as it escapes. Continuous.
- Log time: the probe's position along the curve follows log time (revolutions accelerate).
- Linear time: the whole Earth-escape treatment is skipped (already shipped).

## E. Acceptance test (run BEFORE declaring done)

`tmp/ro/test_escape.py`, over arrival times × Play times × zoom levels, asserts:
1. **Exactly one** green trajectory trace is visible (the hidden helio arc has 0 opacity /
   no second visible curve).
2. Escape root is ON the disk edge: ‖P₀ − Earth‖ = chosen disk radius (±1%).
3. Tangent at the edge: (P₁−P₀) ⟂ (P₀−Earth) (|cos| < 0.02).
4. Curve **ends at the heliocentric probe** p (‖P_last − p‖ small) → cruise continuity.
5. **No loop / no backtrack**: distance-from-start increases monotonically along the curve.
6. No JS errors.
Plus a frame-by-frame screenshot sweep I eyeball before sending.

## F. What I will NOT do
- Send a build before E passes.
- Draw two trajectories.
- Claim "to scale" if you pick the enlarged schematic disk.
