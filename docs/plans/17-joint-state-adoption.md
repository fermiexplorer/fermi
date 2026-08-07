# 17 — Adopt the jointly-validated AC state (Akeson J2019.5, kinematic frame, 2029 departure)

**Issue:** [#17](https://github.com/fermiexplorer/fermi/issues/17) · **Build:** 185

## Why

The engine's carried Alpha Centauri state mixes catalogs (Akeson-consistent
distance, Kervella-era proper motions, spectroscopic RV used as kinematic).
Adopting the jointly-validated golden-fixture-v2 state buys: (1) worst-case
aim bias cut ~2,200 → ~430–535 AU against the 2,600 AU budget (one
self-consistent catalog flown end-to-end); (2) the kinematic RV frame (the
+61.4 m/s one-sided correction, ~+300 yr, now applied instead of omitted);
(3) pinned epochs (state J2019.5, departure origin 2029.0); (4) joint
reproducibility — future differences are inputs by construction, gated in CI.
Mission design is unchanged: the fuel basin is flat, so vehicle sizing and
all Δv/feasibility verdicts stay put. Labels move.

## New carried state (fixture v2, verified through our chain at 1e-15)

| Quantity | Value |
|---|---|
| Position (ICRS, J2019.5) | RA 219.85892215°, Dec −60.83163195° |
| Parallax | 750.81 ± 0.38 mas (Akeson et al. 2021, AJ 162, 14) |
| PM (μα*, μδ) | −3639.95 ± 0.42, +700.40 ± 0.17 mas/yr |
| RV (kinematic frame) | −22.3182 ± 0.0034 km/s = V0 −22.3796 ± 0.0020 (spectroscopic, Akeson 2021) + 61.4 ± 2.7 m/s (Kervella, Thévenin & Lovis 2017, A&A 598, L7) |
| Epochs | state clock from J2019.5; departure origin 2029.0 (offset 9.5 yr) |
| Landmarks | crossing 79,765.87 yr (state clock) = 79,756.37 from departure = AD 81,785.37; v∞ 24.158 km/s; 6.428 ly |

## Steps

1. **Engine**: rewrite the catalog block of `fermi_sim/astro.py` (values
   above, full-precision distance from parallax, conventions documented);
   add state/departure epoch constants.
2. **Landmarks re-derivation** (read-only script): crossing, v∞/β at the
   table epochs, impulsive optimum, min-fuel epoch — the numbers that seed
   every downstream pin.
3. **Deep sim re-fly**: `tools/sim_pp_arrival.py` → new
   `docs/data/pp_arrival_sim.json`; re-measure basin bottom, crossing
   penalty, flyability edge, custody, dt/8 convergence.
4. **Web mirror**: re-dump the baked state into `web/physics.js`; update the
   arrival-slider default/snap (crossing grid point), `atOpt` anchors, epoch
   table, design-window prose; parity refs in `audit/calcs/audit_webjs.mjs`.
5. **Docs one-pass** (per DOC_MAINTENANCE clusters): PP-ARRIVAL-OPTIMUM
   (§1–§7 numbers, kinematic-frame + epoch-origin note, ±400–800 band),
   README, REPORT, index.html, run_analysis, EXTERNAL_AUDIT_SCOPE,
   audit/psi/README, AUDIT_COMPARISON engine columns where stated.
6. **Audit suite re-anchor**: ui_sliders (default T, crossing band, budget,
   wet mass, campaign pin), audit_docs (new positive pins + retire old
   tokens), audit_pumping 13g/13h gates, audit_ephemeris state pins,
   audit_golden 14d restoration pin (79,252 → 79,766).
7. **Archive + gate v2**: revised memo PDF + fixture v2 under `audit/psi/`
   (fixture at `audit/psi/golden_v2/`, sha256-pinned; v1 kept); extend
   `audit_golden.py` with the 15-check v2 section.
8. **Verify**: `tmp/ro/verify_now.py` then `tmp/ro/verify_ui_now.py` — all
   green before release.

## Verification

Full suite green (audits incl. golden v1+v2 gates, parity, UI, pytest);
`run_analysis.py` reprinted and consistent; live-badge poll after deploy.

## Push / merge

Release wrapper `tmp/rw/release_now.py` → `tools/release.py` (deploy: page +
physics.js change), branch `codex/v4-prompt10-audit` + `HEAD:main`, one
commit "build 185: adopt the jointly-validated AC state (#17)", then close
#17 with the shipped record.
