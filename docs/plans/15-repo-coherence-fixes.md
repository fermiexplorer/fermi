# 15 — Apply the repo-coherence-scan findings

**Issue:** #15 · **Status:** shipped (build 182, 2026-08-02) · **Filed:** 2026-08-02

## Background

Owner-ordered whole-repo multi-bot coherence scan (182 agents: 10 lenses → 3
skeptics per finding, 2-of-3 survival). 15 distinct findings confirmed (7 major,
8 minor), 4 refuted. Verdict: **the physics is coherent — engine, JS port, parity
and the tracked data records are clean; every finding is documentation drift**,
concentrated in incomplete build-181 propagation and older re-bake fossils on
surfaces without freshness guards.

## Applied (all prose-only)

- **Build-181 residue sweep**: `audit/psi/README.md` (+0.27→+0.21, +27→+33,
  basin ~75–79.5k, $25k→1.8 kg/$20k, tool reference updated to the deep sim),
  one leftover "+0.27" in PP-NOTES, PP-ARRIVAL-OPTIMUM §7 (+27→+33, 0.08→0.10%),
  §4.1 convergence deltas synced to the JSON, PRECISION_ROADMAP Stage 4, the two
  "<30 m/s" phrasings (REPORT, run_analysis) → "~33 m/s, model-noise scale".
- **Live-convention disclosure rewritten**: the calculator applies NO miss shave
  (raw exact-intercept aim, conservative by ~0.12–0.19 km/s vs the record's
  optimized-offset totals) — the note previously claimed a "max-speed-shave"
  convention it does not use.
- **Shipped-page fixes**: "default ~73k-yr pumped configuration" → crossing-aimed
  ~79.25k; the fuel-optimum tooltip no longer places the crossing at ~73k and is
  architecture-aware; ~162 → ~154 kg; the variations-table Δv decomposition made
  arithmetically consistent (7.7 + 23.9 v∞ + 0.7 tax); optimizer bullet and two
  stale JS comments (4.9→7.9 revs; basin numbers) corrected.
- **Audit-tree snapshots**: AUDIT_COMPARISON animation bullet (4.9→7.9 revs,
  ~12 yr, with the 4.9 figure re-attributed to the bang-bang row);
  EXTERNAL_AUDIT_SCOPE budgets row (→ 32.3 / 31.1 crossing-aim), LOC map
  re-measured (~2290 engine total), suite counts.
- **Suite-count sweep**: 190+/~46/~90 → 230+/49 (~49)/93 across README,
  index.html, AUDIT_COMPARISON, EXTERNAL_AUDIT_SCOPE, audit/README parity/UI
  rows (46/46→49/49, 90/90→93/93).
- **Hardening (the structural fix)**: audit_docs 10c — a retired-number token
  blocklist now also covers the previously unguarded surfaces
  (audit/psi/README, PP-NOTES, EXTERNAL_AUDIT_SCOPE, PP-ARRIVAL-OPTIMUM,
  PRECISION_ROADMAP; audit/fable/ records excluded as designated history), plus
  a corrected-values pin on audit/psi/README.

## Verification

Full `tmp/ro/verify_ui_now.py` green before release (suite grows by the 10c
guards). Scan record: the workflow synthesis is preserved in the issue; refuted
themes (4) were history-snapshot attacks.

## Push / merge

Released via the `tools/release.py` wrapper (deploy: index.html changed); commit
closes #15.
