# Foundations adversarial audit — the arrival-epoch premise, the PSI memo, and the golden fixture

Two linked multi-agent campaigns plus a four-model external verification, run
against the **shared premises** of the 79-kyr arrival model (the linear-kinematics
chain both this project and PSI use), PSI's arrival-epoch memorandum, and the
jointly-agreed golden fixture. Where earlier campaigns verified arithmetic and
implementations, these attack the assumptions both teams stand on — a
common-mode error in the premise would have survived every implementation
cross-check by construction.

## Campaign structure

| Stage | Design | Scale |
|---|---|---|
| Memo/fixture audit | 10 finder lenses → 3 distinct-lens skeptics per finding (default-refute, 2-of-3 survival) → synthesis; full independent reproduction of the memo's kinematic/arithmetic matrix (third + fourth implementations); direct fetches of the cited source papers | 200 agents |
| Foundations audit | 12 premise lenses × 2 independent mandated toolchains (e.g. numerical galactic-orbit integration vs closed-form tidal analysis; astropy/ERFA vs hand-derived perspective terms) → dedup → 3-skeptic verification → completeness critic → synthesis | 122 agents |
| External verification | The same blind prompt pack (8 premise-attack questions, no access to the internal campaigns' findings or to each other) run on four external frontier models: GPT-5.6 Sol (xhigh), Grok 4.5 (xhigh), Gemini 3.5-flash, Gemini 3.1-pro. Reports demanded computed numbers with scripts | 4 independent systems |

## Headline verdicts

**The linear-kinematics chain is positively verified sound.** All five parties
independently bound: galactic differential tide 1–5 AU / ≤1.4 yr over the flight;
perspective acceleration exactly contained in Cartesian `r0 + v·t` (0 by
construction); ICRS/J2000 frame bias < 0.01 yr; every constant in
`fermi_sim/constants.py` at IAU/astropy values to < 0.01 yr of T_cross; ISM drag
and stellar-encounter terms negligible. The engine reproduces the golden fixture
through its own chain at ~1e-15 relative (gate: `audit/calcs/audit_golden.py`).

**The honest uncertainty lives in the catalog inputs, not the model:**

- **Absolute radial velocity**: published catalog sigmas (±2 m/s) are internal
  precision; converting a spectroscopic gamma to a kinematic line-of-sight
  velocity carries zero-point, convective-blueshift-model and orbit-fit terms.
  Five-party floor: 30–100 m/s → ±150–500 yr of T_cross. Empirical anchor:
  three published gammas from the same underlying data span 13.4 m/s. The
  spectroscopic→kinematic gravitational-redshift correction (+61.4 ± 2.7 m/s,
  independently re-derived at +61.3) is real, one-sided, worth ≈ +300 yr.
- **Parallax**: the Kervella 2016 vs Akeson 2021 gap (3.64 mas ≈ 5.1σ formal
  ≈ 530 yr) is the dominant geometric systematic; single-catalog formal bands
  (±55 yr) are under-dispersed. The Gaia-DR3-Proxima adjudication route is
  circular (its line-of-sight depth derives from the Kervella parallax) — the
  two external models that tried it reached opposite verdicts, confirming it
  cannot adjudicate.
- **RV error is along-track**: essentially zero closest-approach miss
  (correlation ~0.007; one internal proof is exact). The 2600-AU requirement is
  therefore scored at closest approach to the AB barycenter — the same error
  model reads ~0.99 pass probability at closest approach vs ~0.80 at a fixed
  instant.
- **Deterministic aim terms** absent from the linear ephemeris, all correctable:
  Proxima's pull on the AB barycenter ~92 AU over the flight (two independent
  two-body integrations: 92.1 / 92–107 AU; timing +2–12 yr); Sun-vs-SSB frame
  ≤16 m/s → ~100–270 AU (a launch-date trim; ≤3 yr of timing); solar-escape and
  AB-gravity bookkeeping ~130 AU combined; probe clock T − t_dep (≈ +12 m/s at
  the 2029 departure target).
- **Compliance**: closest-approach pass probability ≈ 1.00 under formal catalog
  sigmas, ≈ 0.98–0.99 under honest systematic floors, ~0.83–0.88 only when the
  full catalog gap is stressed as a 1σ. Every flown configuration in
  `docs/data/pp_arrival_sim.json` clears the 2600-AU condition.

## Self-corrections (findings against this project's own earlier audits)

Recorded per the audit charter — the campaigns are required to attack prior
conclusions with the same severity as external claims:

1. The memo-audit synthesis initially rejected PSI's ±0.10 km/s RV band as
   "inflated ~50–70× vs published sigmas" and recommended a ±56-yr band. The
   foundations campaign and all four external models independently reversed the
   magnitude: ±0.10 km/s is a defensible absolute-accuracy allowance; the
   provenance criticism stands (the memo derives the band "from the catalog
   sigmas", which the published catalogs do not contain), the magnitude
   criticism is withdrawn.
2. The memo-audit's own "corrected published-Akeson" T_cross (79,433.6 yr) was
   assembled from a J2000 position with J2019.5 observables — a mixed-epoch
   state worth −51 yr. Any epoch-consistent statement differs; the defect class
   it criticized in the memo was present in its own recommendation.

## Memo/fixture findings (summary)

The memo's arithmetic reproduces at machine precision throughout; its
attribution layer contains errors: six values cited to Akeson 2021 (AJ 162, 14)
do not appear in that paper (PM −3644.4/+702.8 ±1.5, RV −22.39 ±0.10 vs the
paper's −3639.95/+700.40 ±0.42/0.17 at J2019.5 and V0 −22.3796 ±0.0020); the
claimed "kinematic −22.204 Proxima constant" exists in no revision of this
repository; the fixture checker's regeneration mode made it its own oracle
(removed in the archived copy, `audit/psi/golden/`); the fixture's 13 values
are themselves quadruply validated and adopted as a permanent gate. The
crossing-epoch design default and this project's 79,252-yr value (as the output
of its carried inputs) are independently endorsed.

## Disposition

Repo-side changes shipped with issue #16 / build 184: the golden-fixture gate,
the AU-space aim budget and honest timing decomposition in
`docs/PP-ARRIVAL-OPTIMUM.md` §5/§5b, closest-approach requirement wording on
all surfaces, and this record. Catalog adoption (which catalog, epoch-consistent
assembly, kinematic-frame labeling) is deliberately deferred — it requires a
single-catalog decision adopted end-to-end; until then every epoch label
carries the §5 astrometry band.
