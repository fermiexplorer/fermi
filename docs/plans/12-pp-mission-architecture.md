# 12 — PP is the mission architecture; alternatives are exploratory (with stated gates)

**Issue:** #12 · **Status:** shipped (build 179, 2026-08-01) · **Filed:** 2026-08-01

## Owner directive

Position perihelion-pumped SEP (PP) as the ONLY realistic architecture — the mission
architecture — and mark every other architecture as an exploratory concept, stating
WHY (the specific blocking gate). Keep all optimizations separate per architecture.
Focus the analysis on PP and study the PSI FINAL paper deeply in that context.

## The WHY, per architecture (as shipped)

- **PP — the mission architecture**: the only one that closes on parts you can order
  today — flown-class 91 W/kg GaAs arrays, NSTAR-class gridded ion inside
  demonstrated life/throughput (needs ~12.4 kh / ~103 kg Xe vs 30,352 h / 235 kg
  demonstrated), MESSENGER-class thermal qualification (established engineering);
  no reactor, no assist, no kick stage; independently cross-assessed end-to-end.
- **Direct SEP** — exploratory; gate: needs vehicle α ≈ 100–130 W/kg → a
  ~1000 W/kg-class array that does not exist (today's hardware: measured
  infeasible, spiral saturates near v∞ ≈ 0).
- **Solar-Oberth** — exploratory; gate: Parker-class heat shield + chemical kick
  stage + assist tour — new engineering this program class cannot carry.
- **Jupiter assist** — exploratory; gate: window-contingent (fixed launch date vs
  synodic phasing) + assist-class deep-space operations (the cost-dominating class);
  the shown Δv is a geometric upper bound.
- **Synchrotron** — exploratory (pre-existing labeling): deep-solar infrastructure.
- **Nuclear-electric** — fallback; gate: no kW-class flight reactor exists to order.

## Shipped surfaces

index.html (architecture radios + architecture-table verdicts + the variations
section reframed "The mission architecture vs the exploratory alternative"),
README.md, docs/REPORT.md (both architecture lists), run_analysis.py verdict.
audit_docs +9 guards pin the labels and the stated gates.
PSI study: `audit/psi/PP-NOTES.md` — the FINAL report read PP-first (what it
establishes for PP, what we extended, what remains open), linked from the archive
README. Candidate next issues listed there (cost/$10M layer; GTO default per their
R1; dispersion surfacing).

## Verification

`tmp/ro/verify_ui_now.py` all green (audits incl. the new 9c guards + parity + UI).

## Push / merge

Released via the `tools/release.py` wrapper (deploy: index.html changed); commit
closes #12.
