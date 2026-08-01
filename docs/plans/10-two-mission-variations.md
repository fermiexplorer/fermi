# 10 — Two mission variations: complete separation of direct vs pumped

**Issue:** #10 · **Status:** shipped (build 175, 2026-08-01) · **Filed:** 2026-08-01

## Background

The direct (Earth-borrow) and perihelion-pumped architectures are **two separate
mission variations** sharing only the top-level requirement. Each has its own
cost structure, hence its own optimal arrival epoch (~72,800 vs ~77,800 yr). The
page melded them: the arrival slider's default (72,800 — Variation A's optimum)
predated the pumped default architecture, so the default state flew Variation B
at Variation A's epoch (measured melding cost: +294 m/s, +2.4 kg wet); the
methodology narrated A's optimum with B parentheticals bolted in; and the
"no Earth-velocity borrow" shorthand wrongly implied the pumped vehicle discards
Earth's 29.8 km/s (external reviewer objection — both vehicles keep it; it is
the campaign's initial condition, not a vector-sum discount).

## Shipped record

- **Root fix:** switching the architecture radio snaps the arrival slider to
  that variation's own fuel optimum (live `minFuelYr`, rounded to the slider
  step); the page's native default is now the pumped variation at its own
  77,800-yr optimum. Default budget 32.6 → **32.3 km/s**, wet 157 → **154 kg**,
  aim tilt −2.4° → **−0.5°**, plane steering ~0.5 → **~0.02 km/s**.
- **New methodology section "Two mission variations"**: measured A-vs-B table
  (Chromium run of the live model, each variation at its own preset + optimum) —
  flight plan, optimum + why, Δv, vehicle (43 kg @129 W/kg far-term vs 154 kg
  @39 W/kg today's), thruster duty (68 mN/3.3 kh/28 kg Xe vs 68 mN/12.4 kh/
  103 kg Xe, NSTAR-bounded), thermal (benign vs 0.42 AU MESSENGER-class),
  custody (<1 yr vs 13–14 yr), cost (PSI: $16M-class, ops-dominated),
  epoch-sensitivity cross-penalties (+0.06 vs +0.29 km/s).
- §1–§2 tagged as Variation A's story; pumped parentheticals removed; slider
  hint explains the per-architecture snap; "no Earth-velocity borrow" reworded
  everywhere (page strings, tooltips, chain, `pumped_departure_dv` docstring)
  to the initial-condition framing.
- Guards: ui_sliders — default arrival = 77.8k = its own minFuelYr, budget pin
  32.3, wet pin 154, two arch-switch snap checks (real clicks); audit_docs —
  32.3 stated + "32.6 km/s" banned on all four headline surfaces.

## Verification

`tmp/ro/verify_ui_now.py` all green (audits + parity + UI incl. the new snap
checks). Trade table numbers reproduced by `tmp/ro/i10_trade_study.py` /
`i10_trade_a2.py` (throwaway launchers).

## Push / merge

Released via `tools/release.py` wrapper (deploy: index.html + web changed);
commit closes #10.
