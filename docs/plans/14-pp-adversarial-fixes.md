# 14 — Apply the PP adversarial-audit findings

**Issue:** #14 · **Status:** shipped (build 181, 2026-08-01) · **Filed:** 2026-08-01

## Background

Owner-ordered deep adversarial audit (126 agents: 10 finder lenses → 3 skeptics per
finding, 2-of-3 survival) of both the PSI final paper's PP-relevant claims and this
project's PP arrival-optimum derivation. 10 distinct findings confirmed (0 critical,
4 major, 6 minor), 2 refuted. Record: `audit/fable/fable-pp-adversarial-audit.md`.
Both headline verdicts stand (the arrival conclusion; the PSI negative-proof); the
corrections below are number- and wording-level.

## Applied

1. **Miss-allowance convention** (major): `sim_pp_arrival.py` now optimizes the
   2600-AU offset direction (speed shave vs tilt buy-down); record re-baked:
   73k penalty +273 → **+211 m/s** (1.8 kg Xe), crossing +26.7 → **+33.4 m/s**,
   bottom 32.204 → **32.198** (still 77,500). One-sided error line restated; the
   live calculator's conservative convention delta disclosed.
2. **Flyability edge** (major): golden steering search in `flyable()`; edge
   65,039 → **64,238 yr**; the page's "65,000 unflyable" row replaced by the
   measured flyable row (33.71 km/s, 14.0 yr); mechanism rewritten as a
   custody-gate policy label (~±1 kyr per gate-year), not a physics wall.
3. **Guard 13h** (major): recorded-aim row replay; two-sided edge check with
   ≥0.5-yr custody margins and a golden steering sweep on the negative side.
4. **PSI corroboration retraction** (major): the "planar column bottoms at 65k"
   story (PSI's flagged seed-scatter outlier misread as a trend minimum) retracted
   in the note and PP-NOTES; replaced by the trend-floor statement (23.74 across
   56–60k; in particular NOT 73k).
5. Minor wording/doc fixes: `abs(β)` z-mirror fold documented; v∞-scaling trend-sign
   comments corrected (conservative); >4° continuation marked an a-fortiori bound
   with its custody caveat (engine + page + JS); "at any steering angle" removed.
6. All corrected numbers propagated in one pass: index (epoch table, variations
   table, pumping section), README, REPORT, run_analysis, PP-ARRIVAL-OPTIMUM,
   PP-NOTES.

## Verification

audit_pumping 78/78 including the rewritten 13h (fresh replay 32,261 vs 32,260;
65k row replays at 13.98 yr; negative probe fails across 18 steering angles);
full `tmp/ro/verify_ui_now.py` green before release.

## Push / merge

Released via the `tools/release.py` wrapper (deploy: index.html + web changed);
commit closes #14.
