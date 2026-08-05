# 16 — Foundations-audit fixes: golden gate, AU-space budget, spec precision

**Issue:** [#16](https://github.com/fermiexplorer/fermi/issues/16) · **Build:** 184

## Context

A foundations-level adversarial campaign (122-agent Claude workflow + four
external frontier models — GPT-5.6 Sol, Grok 4.5, Gemini 3.5-flash,
Gemini 3.1-pro — each run blind on the same prompt pack; reports under
`tmp/wf19/`, synthesis in the session scratchpad) attacked the shared
premises of the 79-kyr arrival model rather than its arithmetic. Verdict:
the linear-kinematics chain is positively verified sound (galactic tide
1–5 AU; perspective acceleration exactly contained; constants clean to
<0.01 yr), but several bookkeeping/spec items are real and repo-fixable now,
independent of the deferred catalog-adoption decision:

- Absolute-RV accuracy: catalog ±2 m/s sigmas are internal precision; the
  honest kinematic-frame floor is 30–100 m/s → ±150–500 yr of T_cross —
  all five families agree (this REVERSES the prior 200-agent audit's
  ±56-yr band).
- RV error is along-track: ~zero closest-approach miss (correlation 0.007);
  the 2600-AU spec must be scored at closest approach to the AB barycenter.
- Proxima deflects the AB barycenter ~92 AU over the flight (two independent
  two-body integrations) — absent from every prior ledger.
- Sun-vs-SSB frame: ~11–16 m/s → 100–270 AU aim term, ≤3 yr timing;
  deterministic, correctable at a fixed launch date (2029).
- "99% of the way" framing: the star is 6.40 ly away at arrival (47% farther
  than today).
- The golden fixture's 13 values are triply validated; its checker's
  `--write` path is a self-oracle and must not enter `audit/` as-is.

## Changes

1. `audit/psi/golden/` — fixture archived (inputs/outputs verbatim from PSI;
   checker with the `--write` regeneration path removed; README corrected:
   input PM/RV relabeled as carried constants rather than Akeson 2021
   centrals, astrometric-epoch note, honest constant-drift detectability
   sentence, scope statement).
2. `audit/calcs/audit_golden.py` — new suite section: sha256-pins both JSON
   files, then runs OUR `fermi_sim` chain under the fixture's pinned
   constants on the fixture inputs and compares all 13 values against PSI's
   oracle at the published tolerances (engine vs independent oracle — never
   checker-vs-itself). Wired into `run_audits.py`.
3. `docs/PP-ARRIVAL-OPTIMUM.md` §5 — AU-space aim-error budget table +
   closest-approach scoring note + shave-convention caveat; timing-band row
   replaced with the honest decomposition (absolute-RV frame + parallax
   systematics + one-sided kinematic correction); probe-clock note
   (T − t_dep, departure target 2029).
4. Requirement wording on all surfaces (README.md, docs/REPORT.md,
   index.html, run_analysis.py, audit/EXTERNAL_AUDIT_SCOPE.md): "within
   2600 AU of the AB barycenter at closest approach"; "99%" claim tied to
   today's separation with the 6.4-ly arrival distance stated.
5. `audit/fable/fable-foundations-audit.md` — campaign record (design,
   findings, self-corrections, null ledger, external-model concurrence);
   `audit/README.md` gains the missing campaign rows.
6. `audit/calcs/audit_docs.py` — guards: closest-approach + AB-barycenter
   phrasing present on requirement surfaces; bare "(99% of the way)" banned;
   AU-space table present; golden gate wired.

## Explicitly deferred

- Akeson catalog switch / epoch-consistent state re-assembly in
  `fermi_sim/astro.py` (moves every public epoch label; requires a
  single-catalog adoption decision first).

## Verification

- `timeout 600 .venv/bin/python tmp/ro/verify_now.py` (audits incl. new
  golden gate + parity + syntax + pytest) — all green.
- `timeout 600 .venv/bin/python tmp/ro/verify_ui_now.py` before release
  (index.html changes).

## Push / merge

- Branch `codex/v4-prompt10-audit` (current working branch), release via
  `tmp/rw/release_now.py` wrapper → `tools/release.py` (commit, deploy both
  Pages clones — index.html changed — push branch + `HEAD:main`, poll the
  live badge). One commit, message "build 184: foundations-audit fixes —
  golden gate, AU-space budget, spec precision (#16)". Close #16 with a
  comment linking this plan.
