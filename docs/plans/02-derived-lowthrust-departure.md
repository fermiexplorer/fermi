# 02 — Derived low-thrust departure Δv (replace the floor+penalty hack)

## Why
The web tool currently sizes the departure Δv as **`impulsive_floor + penalty`** (penalty =
a hand-set slider, default 6 km/s). The impulsive floor assumes an *instantaneous* perigee
burn — physically impossible for an all-ion vehicle (it would need an external high-thrust
stage we don't model). All four audits flagged this as the #1 open item. Goal: make the
departure Δv a **derived low-thrust number**, not a benchmark, while keeping the UI's instant
slider response.

## Performance analysis (the core question)
The Earth-escape spiral (`spiral_escape_dv`) is an adaptive-step RK4 over a many-revolution
low-thrust spiral. Running it **live on every slider tick is not viable** — the arrival slider
continuously changes v∞,E, so each drag step would re-integrate (tens of ms → visible lag).

But we don't need to, because the spiral Δv is a **smooth function of just two inputs**:
`Δv_spiral = f(v∞,E, LEO_altitude)`. It does **not** depend on dry mass, Isp, power, η, tank,
payload, etc. (those only enter the rocket equation afterward), and in the low-thrust limit it
is **independent of thrust acceleration** (Δv = a·t is invariant — see the docstring). So:

**Decision: precompute once, evaluate by closed-form fit (or table interpolation).**
- Offline (Python, build-time), integrate `Δv_spiral(v∞,E)` over v∞,E ∈ [0, 32] km/s at the
  reference altitude, plus a small altitude correction (v_circ, v_esc from `leo_speeds`).
- Fit a low-order closed form (expected `Δv ≈ v_circ + a·v∞,E + b·v∞,E²`, since the crude
  Edelbaum estimate is `v_circ + v∞,E`) — **target < 1 % / few-m/s error** vs the integration.
- Embed the (handful of) fit coefficients in `fermi_sim` AND `web/physics.js`.
- Web evaluation is then **O(1) arithmetic → instant**, identical feel to today, but the number
  is *derived from the real integrated spiral*, not a hand-set penalty.

This is the "precomputed data + interpolation" path; no live integration, no pykep in the
browser, nothing heavy. (Adaptive live integration was the alternative — rejected on latency.)

## Decision (locked): do A, then B
Both phases ship. **Phase A** lands first (removes the hack, derived, instant). **Phase B**
then refines the Earth-escape spiral with perigee-biased thrusting to recover the realistic SEP
optimum. Both are precomputed → instant; both are fully derived (no hand-set penalty).

| Phase | What it derives | 73k departure Δv | Xenon (Isp 3000, 255 kg dry) | Status |
|---|---|---|---|---|
| (current) floor + 6 penalty | hand-set | ~20 km/s | ~248 kg | **the hack we're removing** |
| **A — naïve spiral** | integrate constant-tangential spiral | ~25 km/s | ~344 kg (57 %) | ship first |
| **B — perigee-biased optimised** | duty-cycled spiral, minimised over the gate | ~18–22 km/s | ~250–290 kg | ship second (refines A) |

**Headline impact:** A *raises* the baseline (~248 → ~344 kg) — more conservative/honest; B then
brings it back toward today's value, but *derived* rather than assumed. The design **closes** at
all three (audit v04: even the spiral-bound case leaves ~141 kg of the 255 kg dry bus after
array+engine+tank) and stays inside 100 kyr / 2600 AU, so feasibility is unchanged throughout.
The impulsive floor stays visible only as a labelled *theoretical lower bound (needs a high-thrust
stage — not this vehicle)*; A and B are the bracket's interior, now both derived.

## Auditability (100% — hard requirement)
Every derived number must be independently reproducible and checked by a *different* method
(keeping the `audit/` independence rule — never engine-vs-itself):
- **Reproducible fit.** The fit/table coefficients are emitted by a committed generator
  (`tools/fit_spiral.py`) from `spiral_escape_dv`; the script prints the coefficients AND the
  max fit error, and is re-runnable. No magic constants — each is traceable to the integration
  that produced it (and the integration to the equations of motion).
- **Independent re-derivation in `audit/calcs/`.** New checks: (i) fit/table vs a fresh
  integration < 1 % across v∞,E∈[10,25]; (ii) naïve spiral vs the analytic Edelbaum estimate
  `≈ v_circ + v∞,E` (different method); (iii) **Phase B**: the perigee-biased optimum re-found by
  an independent minimiser + energy/impulse bookkeeping along the arc, and confirmed to sit in
  `[impulsive_floor, naïve_spiral]`; (iv) accel-invariance (low-thrust limit) holds.
- **Cross-implementation parity.** `node audit/calcs/audit_webjs.mjs` proves the JS departure Δv
  equals Python to machine precision (the embedded fit coefficients match).
- **Third-party re-audit.** Add an `AUDIT_PROMPTS.md` entry that hands an outside agent the method
  and the numbers to independently re-derive A and B (matching prompts 1–10), and re-run the
  Codex/Grok/Gemini suites so all four reconfirm.
- **Provenance in docs.** `docs/REPORT.md` / methodology copy states the derived Δv, the method,
  the bracket, and links the generator + audit so any reader can reproduce it.

## Implementation — Phase A (naïve spiral), then Phase B (perigee-biased)
### Phase A — derived naïve spiral, shipped
1. **`fermi_sim/departure.py`** — add `lowthrust_departure_dv(v_inf_sun, plane_angle_deg, alt)`
   that returns the derived spiral Δv via the fitted function; generate+commit the fit
   coefficients from `spiral_escape_dv` (a small `tools/fit_spiral.py`, or a module constant
   with a comment showing the integration that produced it). `departure_budget` returns this as
   the design Δv; the impulsive floor stays as a separate `dv_impulsive` reference field.
2. **`web/physics.js`** — mirror the same fit coefficients and formula (this is the source of
   truth rule: change Python first, then port). Remove the `pen` penalty from `dvDesign`; keep
   `SPIRAL_MAX` only if still used as a sanity band.
3. **UI (`index.html`)** — remove/replace the "low-thrust penalty" slider; relabel the floor in
   the Δv breakdown as the theoretical impulsive minimum (not flyable by this vehicle); update
   the methodology copy and the summary line. Bump build.
4. **Audit (`audit/calcs/`)** — new independent check: the embedded fit agrees with a fresh
   `spiral_escape_dv` integration to < 1 % across v∞,E; update `audit_departure.py` expectations;
   re-run the full suite + web parity.

### Phase B — perigee-biased optimised spiral, shipped after A
5. **`fermi_sim/departure.py`** — `perigee_biased_dv(...)`: integrate a duty-cycled spiral
   (thrust while `r < k·r_perigee`, coast otherwise) and minimise Δv over the gate `k` (1-D
   golden-section, the same `_golden_min` already in `spacecraft.py`). Returns the optimum Δv,
   the optimal gate, and the thrust/coast profile.
6. Refit/retabulate `Δv_optimised(v∞,E, alt)` from this optimum; swap it in as the design Δv
   (naïve spiral retained as the conservative upper bracket and a sanity bound).
7. Mirror coefficients to `web/physics.js`; re-run parity; update UI copy (now "perigee-biased
   SEP, derived"); bump build.
8. Add the Phase-B audit checks listed under **Auditability** (independent minimiser, energy/
   impulse bookkeeping, bracket containment).

## Validation / acceptance
- Fit vs integration: max error < 1 % (few m/s) over v∞,E ∈ [10, 25] km/s (the feasible band).
- `audit/calcs/run_audits.py` green; `node audit/calcs/audit_webjs.mjs` parity green
  (Python and JS produce identical departure Δv).
- `ui_sliders.py` updated for the removed penalty slider; instant slider response preserved
  (no integration on the hot path — verified by the closed-form eval).
- Derived Δv lands inside the analytic [impulsive_floor, naïve_spiral] bracket.

## Push / merge
- Branch off `main` (e.g. `derived-lowthrust-departure`); commit `fermi_sim` change first, then
  the mirrored `web/physics.js`, then UI + audit, each its own commit.
- Open a PR; CI = the audit suite + parity + pytest must pass.
- Deploy a new versioned web build (b<N>.html + index.html) into both Pages clones the usual way.

## Verification steps (post-merge)
1. `.venv/bin/python audit/calcs/run_audits.py` → all pass (incl. new fit-vs-integration check).
2. `node audit/calcs/audit_webjs.mjs` → parity pass (JS departure Δv == Python).
3. `.venv/bin/python tmp/ro/check_58k.py` → 58k/73k departure Δv now = derived spiral value.
4. Live: drag the arrival slider — confirm the response is still instant (closed-form eval).
5. Confirm the page no longer exposes the penalty slider and labels the floor as a reference.

## Out of scope (this pass)
Heliocentric-leg low-thrust losses with 1/r² solar falloff (plan 01 phase 2), launch-window
phasing, gravity assists as phased solutions. Phases A and B both model the **Earth-escape**
spiral as the derived replacement for floor+penalty; the heliocentric v_dep relation is unchanged
until plan 01 phase 2.
