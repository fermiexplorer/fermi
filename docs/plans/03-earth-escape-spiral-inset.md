# 03 — Earth-escape spiral inset (the missing many-revolution view)

## Why
The 3D views are solar-system scale (AU → ly), so the **geocentric Earth-escape spiral** — the
many-revolution climb out of Earth's well that *dominates* the ion departure Δv — is a sub-pixel
dot at the launch point and is never seen. Users (correctly) notice the visible spiral is ~1
revolution. That visible loop is the **heliocentric** (solar) escape; the Earth spiral is a
separate, ~10⁷-smaller phenomenon. This inset draws it, so "ion departure costs ~25 km/s because
it takes ~1000 revolutions" becomes visible, not just a number.

## Rev-count & time model (grounded — see tmp/ro/revcount.py)
Integrating the geocentric spiral from a 590 km LEO to Earth-escape (C3 = 0) at the real
thrust-to-weight gives a remarkably clean law:

- **Revolutions: N = K / a**, with **K ≈ 0.3266** (constant to 4 sig figs across a = 10⁻⁴…10⁻³ m/s²);
  a = thrust/wet mass (the *real* spacecraft acceleration, already computed as `r.thrust/r.wet`).
- **Time: t_escape ≈ v_circ(perigee) / a** (spiral-to-escape Δv ≈ v_circ).
- **Escape radius ≈ 150 R⊕** (well inside Earth's Hill sphere, ~235 R⊕).

At the baseline (a ≈ 3.3×10⁻⁴ m/s², ~3.4×10⁻⁵ g): **~990 revolutions, 0.68 yr.** Lighter/higher-power
→ higher a → fewer revs; the count is fully **design-responsive** and **instant** (a closed form, no
live integration). K depends weakly on perigee (via v_circ) — fit K(perigee) offline (one extra
coefficient) so the inset tracks the perigee slider.

## What the inset draws (2D geocentric — clearest for revolutions)
- Earth at centre; the LEO start; the **expanding spiral from LEO to escape**; a faint Hill-sphere
  ring; the probe's current position; "escaped" once past C3 = 0.
- Labels (exact, design-responsive): **≈N revolutions · t_escape yr · Δv_earth ≈ v_circ km/s**.
- **Drawing density:** N (~1000) literal loops are an unreadable blur in a small panel, so draw a
  **representative ~50–60 loops** (a parametric near-circular spiral r(τ), θ(τ) from LEO radius to
  escape radius) and **label the true N**. The drawn loops convey the tight winding; the number is
  honest. (Alternative: all N loops at low opacity — rejected as a blur. Flagged for your call.)

## Animation (synced to elapsed time — your "faster and faster" point)
The probe's position maps from the **current elapsed time** `craftState().es` into the burn window
[0, t_escape]:
- **Log time (default):** es grows exponentially with animU, so during the first ~10% of Play the
  probe **sweeps the revolutions faster and faster** — exactly the effect you described.
- **Linear time:** the whole spiral is the first instant (animU < ~2×10⁻⁵) — the probe is already
  escaped for essentially all of Play; the inset shows the completed spiral. (Honest: the burn is
  ~1 yr of ~75,000.)
- After `es > t_escape`: full spiral + "escaped Earth — now heliocentric."
Static when paused; advances with Play and with the burn-timeline scrub.

## Placement
A compact inset panel (≈ chase-cam width) added to the trajectory section — proposed under the
burn timeline, captioned "Earth-escape spiral (geocentric · within Earth's Hill sphere)". It is
a *2D* panel (no camera sync; the 3D group is unaffected). Optional later: a small zoom toggle.

## Implementation
1. **`fermi_sim/departure.py`** — `earth_escape_revs(thrust, mass, perigee_km)` → (N, t_escape_yr,
   r_escape) via the K/a law (K fit by the generator). Add to the spacecraft summary so it's audited.
2. **`web/physics.js`** — mirror `earthEscapeRevs` + the K coefficient(s). `index.html` computes N/t
   from `r.thrust/r.wet` and the perigee.
3. **`index.html`** — `drawEarthSpiral(r,c)`: a Plotly 2D inset (parametric spiral, capped loops,
   probe marker at the es→spiral mapping), wired into `drawViz()` and the scrub; a new chart div +
   caption. Bump build.
4. **`tools/fit_spiral.py`** — emit K (and K(perigee)) reproducibly. **`audit/calcs/`** — new check:
   the K/a rev law matches a fresh geocentric integration (N within a few %), and N ∝ 1/a.

## Validation / acceptance
- Rev law vs integration < ~3% over a ∈ [10⁻⁴, 10⁻³]; N ∝ 1/a confirmed (N·a constant).
- Baseline shows ~1000 revs, ~0.7 yr; raising power/Isp visibly lowers the count.
- Inset animates in sync (faster-revs in log, instant in linear); no JS errors; instant slider
  response (closed form).
- Full audit suite + JS↔Py parity green; pytest green.

## Push / verify / deploy
- Commit `fermi_sim` first, then mirror `web/physics.js`, then the UI + audit (each its own commit);
  fast-forward `origin/main`; deploy a versioned inlined build into both Pages clones; poll live.

## Out of scope
3D geocentric view; eclipse/J2/perigee-drift during the spiral; the real per-rev Δv profile (we use
the clean near-circular law). Chemical/elliptical-start effects on N can fold in later via K(a, e).
