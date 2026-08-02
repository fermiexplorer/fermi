# PSI external assessments

Two documents from Physical Superintelligence PBC are archived here with attribution as
the independent external cross-assessment of this project — both produced and verified
end-to-end by PSI's autonomous physics-research platform:

- **`PSI_FermiExplorerInterstellarPrecursor_FeasibilityAssessment.pdf`** — *Interstellar
  Precursor Mission to Alpha Centauri: Technical Feasibility Assessment*, July 2026,
  **Final**. The authoritative version: staged independent audit, a certified lower-bound
  proof with adversarial audit, a converged three-dimensional trajectory verification, and
  a seeded execution-dispersion analysis.
- **`PSI-TR-2026-0714.pdf`** — the earlier **working draft** of the same assessment
  (kept because in-repo prose and audit records cite it by TR number).

## What the assessment contributes

- **Confirms the geometry**: optimum 73,012 yr (ours 72,800/72,600), tilt 2.48° (2.4°),
  impulsive floor 13.85 km/s (13.88), tangential intercept 58,422 yr (58,138), closest
  approach 27,955 yr @ 3.15 ly (27,960 @ 3.13) — "agreement to 0.3% or better; aim tilt
  to 0.09° absolute" (their §2.4) — and all five of this project's arrival-time intuitions
  (their "Design Intuitions Examined").
- **Source of the perihelion-pumping closure**: the outward-spiral power wall is a
  property of the trajectory class; a pumping trajectory at a₀ = 2.5×10⁻⁴ m/s² (today's
  hardware) reaches the full cruise. Their optimized 12-yr schedule costs Δv 23.97 km/s
  (production timestep; 23.985 quarter-step, carried as 24.0); certified heliocentric
  lower bound 16.56 km/s (throttleable class, unconstrained time, r_p ≥ 0.42 AU) with an
  unconstrained-time integrated schedule at 18.87 km/s (~58 yr powered).
- **Departure accounting**: SEP total from LEO 30.5–31.6 km/s (7.6 escape + 22.9–24.0
  heliocentric reference interval); GTO drop-off cuts 7.6 → 4.24 km/s and closes a
  ~100 kg vehicle (their recommendation R1); mass-closure boundary 113.5–146 kg from LEO.
- **Measured out-of-plane cost** (final report): a fully three-dimensional
  re-optimization prices the 2.48° departure tilt at **0.58 km/s** — inside the planar
  bracket [22 m/s, 1.02 km/s], and 0.57× the conservative v∞·|sin β| bound this project
  prices (see cross-validation below).
- **Targeting & cost** (final report): open-loop pass probability 0.982 under their
  stated error budget (20,000-draw seeded Monte Carlo, dominated by thrust-magnitude
  knowledge); program cost median $15.7–16.6M vs the $10M target, with the gap
  programmatic (bus + operations), not physical.
- **Independent target screening**: LSPM J2146+3813 best (impulsive floor 9.30 km/s @
  78 kyr; published encounter 0.568 pc @ +82.5 kyr matches our catalog 0.570 pc @
  82.7 kyr), λ Ser best solar-type second (11.38 km/s @ 151.6 kyr), α² Lib excluded,
  full Bailer-Jones catalogue sweep finds nothing better.

## Our cross-validation of it (engine + adversarial audits)

`crosscheck_final.py` (run from the repo root) re-derives every engine-comparable
headline of the final report with `fermi_sim` and prints measured deltas. Findings:

- **Arrival-epoch trade (their Table 14, 55–85 kyr)**: impulsive floor agrees to
  ≤30 m/s (mean +17 m/s) across all 31 rows; v∞ to ~0.1 km/s (our exact-intercept
  values sit above theirs, our full-2600-AU-shave values below — their miss-tolerance
  handling lands between, as expected); aim tilt to ≤0.19°.
- **Landmarks**: our floor argmin 72,600 yr @ 13.80 km/s vs their 73,012 @ 13.85 — the
  basin is flat to ±2 m/s over ±1 kyr, so the offset is immaterial. Ecliptic crossing:
  ours 79,252 yr vs their 79,786; the 534-yr offset is fully explained by the ≤0.19°
  tilt offset from sub-0.5% astrometry-input differences (tilt slope 0.332°/kyr →
  0.18° ≈ 540 yr). Adopted-state deltas: d 4.344 vs 4.365 ly, v_t 23.272 vs
  23.38 km/s, v_r −22.40 vs −22.40 (their stated worst-case replication tolerance is
  0.5%; ours vs theirs sits inside it).
- **Outward-spiral ceilings**: ours 0 / 1.9 / 15.9 km/s vs theirs 0 / 3.4 / 17.0 at
  a₀ = 1.5/5/10×10⁻⁴ m/s² (constant-tangential prograde policy; their own
  two-integrator band is 2.7% and the mid-band difference is policy-dependent — both
  sit far below the 23.38 km/s cruise floor everywhere, which is the decisive claim).
- Pumping mechanism reproduced with an independent bang-bang policy
  (`fermi_sim.departure.perihelion_pumped_vinf`): 23.66 km/s at the design point,
  Δv 25.63 (theirs 23.97 optimized), 9.6 yr (theirs 12.0), 4.9 revolutions. The
  +1.66 km/s premium of our policy is almost entirely in the cruder retrograde
  pump-down; the prograde legs agree to ~2%.
- Their optimised-schedule result independently confirmed — and slightly beaten — by our
  own optimiser (`fermi_sim/pump_schedule.py` + `tools/optimize_pump_schedule.py`,
  issue #4): at the same 12-yr custody our anchored optimised schedule costs
  **Δv 23.14 km/s vs their published 23.97** (−3.5%) under identical physics assumptions
  (their idealised 4× perihelion power cap); our unconstrained frontier point (22.84 at
  28.5 yr) is consistent with their certified bracket [16.56, 18.87].
- **Mass-closure algebra** (their Appendix C) replayed independently: LEO boundary
  113.1 kg @ Δv_hel 22.9 / 146.0 kg @ 24.0 vs their 113.3/145.6; GTO 62–72 kg vs their
  59–68 (every ≥80 kg GTO case closes in both). Our engine's own closure formulation
  (`minimal_dry_mass` fixed point, their component set) lands 134.6 kg wet / 68%
  propellant — the same vehicle class.
- **Out-of-plane pricing**: our v∞·|sin β| term charges 946–1023 m/s at the 73-kyr aim —
  the conservative (planar-bracket-upper) end; their measured 3-D increment is 578 m/s.
  Re-running our pumped-budget arrival-epoch scan with the tilt term scaled to their
  measured pricing leaves the fuel-optimum at the 79,250-yr crossing unchanged (the
  |sin β| corner still dominates the smooth v∞+tax slope ~2×).
- **Alternative targets** from our own web-catalog states: LSPM J2146+3813 floor
  9.31 km/s @ 78.0 kyr (theirs 9.30 @ 78.0), perihelion 0.570 pc @ 82.7 kyr (published
  0.568 @ 82.5); λ Ser floor 11.38 @ 151.5 kyr (theirs 11.38 @ 151.6).
- Note on comparability (issue #5): the calculator's shipped default prices the
  campaign under a power curve DERIVED from the array's own energy balance
  (`fermi_sim/thermal.py`; cap_eff(0.42 AU) = 3.54, not 4×), costing 24.44 km/s at the
  same custody — between their cap-4 (23.97 @ 12 yr) and cap-3 (24.10 @ 19.7 yr)
  sensitivity rows, without extending the powered horizon. All numbers compared against
  PSI in this repo are computed at their 4× assumption unless explicitly labelled thermal.
- Contiguous working-region edge a₀ ≈ 2.24×10⁻⁴ m/s² (validated by three independent
  integrators; success below is phasing-dependent and non-monotonic — see
  `audit/fable/fable-pumping-synchrotron-audit.md`). Their pumping-feasibility floor is
  the same number (a₀ ≳ 2.25×10⁻⁴, their §5.3).
- **Arrival-epoch scope finding**: their 73,012-yr optimum is correct for what it is —
  the argmin of the IMPULSIVE / Earth-relative departure budget (we corroborate it to
  0.2%, and their blind re-derivation confirms it independently). It is **not** the
  pumped mission's arrival optimum, and the report itself never claims it is: the
  pumped column of their Table 14 "is planar and excludes the cost of acquiring the
  out-of-plane aim tilt", §2.5 leaves the trade "unsettled ... future work", and
  recommendation R6 lists pricing the tilt across arrival geometries as the natural
  next computation. Performing exactly that computation (derived 3-D tilt pricing +
  per-epoch full-campaign simulation, `tools/derive_epoch_table.py`) puts the pumped
  fuel basin at ~77–79.3 kyr — the 73k epoch costs the pumped vehicle +0.27 km/s
  (direct simulation, no closed-form budget in the loop) — with the geometry-anchored
  79,252-yr ecliptic crossing adopted as the design epoch (+27 m/s vs the basin
  bottom, inside model noise). In program-cost terms the whole 73–79k epoch span is
  worth ~$25k of xenon + launch mass under their own cost model — three orders of
  magnitude below their ops/custody cost drivers — so the epoch refinement changes
  fuel bookkeeping, not the cost verdict. One dimension does survive in favour of
  their 73k quoting: the ARRIVAL DATE itself. Because the window is flat in both
  fuel and cost, aiming at its early end arrives ~6,000 yr sooner for a
  rounding-error price — a legitimate second optimization axis (arrival value)
  orthogonal to fuel. The defensible statement is therefore: the pumped design
  epoch is the flat window [~73k, ~79.3k]; the crossing end optimizes fuel and
  geometric robustness, the 73k end optimizes arrival date; PSI's number is the
  latter (implicitly), not a derived fuel optimum.
- Their independent-model concurrence claims are consistent with our independent audits
  (astropy, GMAT, Codex/Grok/Gemini/Fable re-implementations).

Validated design profile adopted from this work: `fermi_sim.constants.PUMP_DESIGN_A0`
(2.5×10⁻⁴ m/s²) and `PUMP_DESIGN_ISP` (2800 s).
