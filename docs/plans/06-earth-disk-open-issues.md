# 06 — OPEN: Earth-escape disk visualization still has visual issues

**Status: OPEN — deferred.** The user reported "things are still broken" with the
chase-cam Earth-escape disk/escape visualization (Plans 05) and asked to mark it as an
open issue to fix later, rather than continue iterating now.

## What works (build 53)
- Round Earth sphere + round green disk (cubic aspect) in the geocentric view.
- Dawn-dusk orbit plane (disk ⊥ the Earth→Sun line).
- A few tight orbit-raising turns at the very start (fade by ~0.1% of the slider), then a
  pure green disk = the wound-up spiral (real Δr/rev ≈ 4π·a·r³/μ, sub-km at LEO).
- Escape leaves the disk EDGE tangentially during the transition; the root shrinks to
  Earth's centre at the hand-off to the heliocentric arc.
- Burn-timeline Earth-escape segment aligned to the real geocentric escape time (0.70 yr).

## Build 55 — tangent-by-construction escape + exact SOI (RESOLVED the tangency complaint)
- **Exact disk diameter**: `earth_soi_radius()` (engine) = a·(μ⊕/μ☉)^(2/5) = 9.246×10⁸ m ≈
  145.13 R⊕ → disk diameter 0.01236 AU. Mirrored to `physics.earthSoiRadius`, JS↔Py parity.
- **Escape curve tangent BY CONSTRUCTION**: P(s) = E + t̂·(rDisk·A·s) + r̂_out·(rDisk·B·s²),
  E on the disk edge, so dP/ds|₀ = t̂·rDisk·A ⟂ radius. In the dawn-dusk plane; scales with the
  rendered disk radius → tangent at the edge at ANY zoom (fixed the out-of-plane Bézier loop).
- **Dot rides the curve** per log-time; orbit-raising dot rides the disk edge.
- **Test**: `tmp/ro/test_tangent.py` — 48 combinations (3 arrival angles × 4 Play times × 4
  zoom levels), asserts escape rooted on the edge, tangent (⟂ radius), and in-plane. ALL PASS.
  (Tangency is a 3D property → preserved under every camera projection.)

## Known remaining rough spots (to revisit)
- The transition (≈1 yr) hand-off from the disk-view escape curve to the real heliocentric
  arc can still look imperfect (shape change between the tangential Bézier and the true
  spiral-out arc; possible minor aspect/grid changes at the regime boundary).
- General "still broken" feedback from the user was not fully diagnosed — needs a fresh
  look at the whole earth→sun→cruise sequence in motion (not just stills), ideally with the
  user pointing at the specific frames.
- Consider whether the disk-view escape should be derived from the real heliocentric arc
  (projected/rooted on the disk edge) rather than a schematic Bézier, for exact continuity.

## Not in scope of this issue
- Linear-time clock, the two rotation KPIs, and the 58k-xenon question are handled
  separately (build 54).

## Next step when resumed
Watch the chase cam through a full Play in log time with the user, capture the exact
frame(s) that look wrong, diagnose root cause, then fix. Re-run tmp/ro/test_diskcam.py +
ui_sliders + parity before shipping.
