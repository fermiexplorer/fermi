# 08 — Pure-ion text rework + pointing/GNC error sliders

> **STATUS (build 60): IMPLEMENTED.** Physical model (user's choice). Two sliders added
> (Injection pointing error 0–3°, GNC pointing error 0–10°); engine fns injection_pointing_dv /
> gnc_steering_factor (mirrored to physics.js, parity 17/17). Departure Δv = spiral·sec(σ_gnc) +
> 2·v_circ·sin(σ_inj/2). New KPIs "Navigation margins" and "Chemical-boost option" (secondary
> comparison). Text reframed: pure-ion baseline + chemical boost as comparison. ui_sliders 56/56,
> pytest 8/8.

## A. Text rework — pure ion primary, chemical boost as a secondary comparison
The page already flies the **derived low-thrust ion spiral** as the real Δv. Today the impulsive
floor is framed dismissively ("not this vehicle / needs a kick stage"). Reframe it as an explicit,
useful **secondary comparison**: *"with an initial chemical boost stage, the ion engine would only
need to provide ≈ floor Δv, cutting the xenon from X→Y kg — at the cost of carrying the stage."*
- Keep the chartDv "impulsive floor" line, relabel "with a chemical boost (comparison)".
- Audit prose (methodology, KPI descriptions, hints) so pure-ion is the consistent baseline and the
  chemical boost reads as an optional trade, not an unreachable footnote.
- No physics change for this part — wording + one comparison callout/KPI.

## B. Two new error sliders (margins → extra Δv → more xenon)

Both are RMS pointing inaccuracies that the ion engine must pay for in extra Δv. **Engine-first**
(fermi_sim), mirrored to physics.js, parity-checked.

1. **Injection pointing error** σ_inj (deg) — error in the LEO injection velocity direction. A
   direction error σ at the parking-orbit speed costs a correction Δv to re-aim onto the right
   departure asymptote:  **Δv_inj = 2·v_circ(alt)·sin(σ_inj/2)**  (≈ v_circ·σ in rad).
   - e.g. 1° at 590 km (v_circ≈7.6 km/s) → 0.13 km/s. Range 0–3°, default 0.5°.

2. **GNC pointing error** σ_gnc (deg) — RMS thrust-pointing inaccuracy through the orbit-raising
   spiral & escape. Off-axis thrust gives a **cosine steering loss**: only cos σ is useful, so the
   spiral Δv inflates by **sec(σ_gnc):  Δv_spiral_eff = Δv_spiral / cos(σ_gnc)** (penalty = sec−1).
   - e.g. 5° → +0.38 % (~0.1 km/s on 25 km/s). Range 0–10°, default 2°. (Honestly second-order — the
     long spiral averages random pointing — but real and design-relevant.)

**Total departure Δv = Δv_spiral / cos(σ_gnc) + Δv_inj**, fed into the rocket equation (propellant,
wet mass) exactly like today's dvDeliver. New KPI shows the two margins and their xenon cost.

### Engine / parity
- `injection_pointing_dv(sigma_deg, alt_km)` and `gnc_steering_factor(sigma_deg)` in
  `fermi_sim/departure.py`; mirror `injectionPointingDv` / `gncSteeringFactor` in web/physics.js;
  add JS↔Py parity checks. `compute()` applies them to dvDesign/needAt.
- UI: two sliders under Departure (deg, with live km/s readout). URL_KEYS += the two.
- ui_sliders: assert raising either slider raises Δv and xenon; zero → unchanged.

## C. Verification
- pytest 8/8, parity (new checks), ui_sliders (new checks), node webjs parity.
- Screenshot the Departure panel with the new sliders + KPI.

## Push/deploy: build NN, standard inline deploy to both Pages clones.
