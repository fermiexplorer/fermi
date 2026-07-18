# Fable multi-agent adversarial audit — perihelion pumping + perihelion synchrotron

**Scope:** the build 124–125 additions — `fermi_sim/departure.py::perihelion_pumped_vinf`,
`pumped_departure_dv`, `synchrotron_escape`, their `web/physics.js` mirrors, the calculator's
"Perihelion-pumped SEP" and "Perihelion synchrotron (lasso)" architecture options, and every number
published in the page's pumping/synchrotron sections.

**Method:** 31 agents in a two-phase adversarial workflow. Phase 1: six independent auditors, each
re-deriving one attack surface with their own scripts (own integrators — 6-state RK4 with in-stage
mass flow, scipy DOP853, scipy solve_ivp — hand vis-viva/Kepler math, and line-by-line JS↔Python
semantic diffs; scripts under `tmp/ro/fable_*`). Phase 2: every reported discrepancy handed to an
independent verifier instructed to REFUTE it (default-refute bias). 25 discrepancies were raised;
**19 survived adversarial verification** (7 major, 12 minor); 6 were killed as not-a-defect.

## Headline verdicts

| Area | Verdict |
|---|---|
| Pumping design point (a₀ 2.5×10⁻⁴ → 23.66 km/s, Δv 25.6, 9.6 yr, 4.9 revs) | **CONFIRMED** by two independent schemes at multiple step scales (<0.2%) |
| Pumping failure point (1.5×10⁻⁴ strands ~15.5 km/s) | **CONFIRMED** (genuine strand, not a timeout artifact) |
| Contiguous working-region edge ≈ 2.24×10⁻⁴ | **CONFIRMED** (step-converged bisection) |
| "Fails below 2.25×10⁻⁴" as a monotone threshold | **REFUTED** — success island at 1.75–1.88×10⁻⁴, strand bands 1.9–2.2×10⁻⁴ and ~2.9–3.1×10⁻⁴ |
| Synchrotron model (all four published cases, escape-termination, periods) | **CONFIRMED** by independent Kepler math + numerical two-body propagation |
| JS ↔ Python mirrors | **CONFIRMED** (no semantic divergence found, including non-default optional args) |
| Rocket-equation closure, work–energy, thermal floor, power cap | **CONFIRMED** (mass closure exact; min solar distance 0.423 AU) |

## Confirmed findings and disposition (all addressed in build 126 unless noted)

### Major

1. **Non-monotonic pumping feasibility** (pump-reintegrate, pump-physics, pump-budget — found
   independently three times). The bang-bang policy's success is phasing-sensitive, not
   threshold-like: island at a₀ ∈ [1.75, 1.88]×10⁻⁴ (reaches in 17–38 yr), strand bands at
   1.9–2.2×10⁻⁴ and 2.9–3.1×10⁻⁴ (better vehicles fail; also cap = 3.0 or 5.7 at the design a₀
   strand). *Fixed:* docstring and page fine print state the geography; run_analysis §7c reworded;
   the calculator gate now retries a **throttled 2.5×10⁻⁴ profile** when a stronger vehicle lands in
   a stall band (a vehicle with more thrust can always fly a weaker profile), and the failure message
   no longer states the wrong reason.
2. **Docstring published a policy the code does not implement** ("outer-third retrograde / prograde
   r < 1.3·rp" — implementing it literally strands at the design point). *Fixed:* docstring now
   describes the actual gates (inertial-side bootstrap, |ν−π| < 60° pump-down, |ν| < 70° staircase
   with the E < −30 km²/s² escape guard, continuous finisher).
3. **"Vehicle α ≈ 13–25 W/kg" low edge impossible.** α = (a₀·vₑ/2η)·(m_wet/m_dry); the manoeuvre's
   own Δv fixes the wet/dry ratio at 2.4–3.4, so the honest band is **≈ 15–21 W/kg**; a 13 W/kg
   vehicle lacks the Δv capacity at Isp 2800. *Fixed:* all α claims updated (page ×3, REPORT,
   run_analysis).
4. **Out-of-plane aim not covered by the 2 km/s tax.** The pumped campaign is integrated in-plane;
   at the 58 kyr tangential aim the out-of-plane component is 4.08 km/s ≫ tax. *Fixed:*
   `pumped_departure_dv` now takes the tilt and charges a first-order plane change v∞·|sin β|
   (engine + JS + parity + UI derivation panel), restoring a sane arrival optimum for the pumped
   budget.
5. **The 2 km/s tax is a single-point calibration.** True tax from the engine's own integrator:
   +3.1 to +8.3 km/s for 15–20 km/s targets (near-fixed pump-down cost), −0.2 to −4.3 km/s for
   28–30 km/s targets at high a₀. *Fixed (documented):* docstring + page state the calibration
   corridor and mispricing direction; fitting tax(a₀, v∞) is follow-up work alongside the
   closed-form re-derivation.

### Minor

6. `audit_pumping.py` threshold bisection rested on a false bracket premise (1.8e-4 "known-fail"
   actually succeeds — it is in the island). *Fixed:* bracket now starts from a verified strand at
   2.2×10⁻⁴, with new checks asserting both the bracket premise and the island's existence.
7. Achieved v∞ above target (23.66, 23.8) is one-step discretisation overshoot, converging to
   23.64 with finer steps. *Fixed (documented)* in docstring + page fine print.
8. Cap-halving cost misquoted: measured +1.06 to +1.16 km/s (not ~1.9), and the omitted real cost is
   the campaign time doubling (9.6 → 18.3 yr). *Fixed* in the page caveat.
9. Osculating perihelion latches ~0.2% under the 0.42 AU floor (0.4192 AU; actual trajectory min
   0.4225 AU). *Fixed (documented)* in the caveat. Immaterial.
10. √(μ⊕/a) escape-leg conservatism is real but small (0.25–0.45 km/s) — it is not a buffer for the
    plane change. *Addressed* by finding 4; docstring quantifies the margin.
11. Synchrotron `reached` could report success on max_passes exhaustion inside the 0.999 tolerance
    window. *Fixed:* `reached` now requires the loop to actually leave at ≥ v_target (engine + JS),
    with a regression check in `audit_synchrotron.py`.
12. `rendezvous_vel` = (√2−1)·v_circ is the near-escape worst case, not the per-pass value.
    *Fixed:* labelled as worst case in the KPI and code comments.
13. The fuel-optimum scan degenerates to the scan floor (58,000 yr) under the synchrotron (Δv flat
    in T). *Fixed:* the optimum is defined as the chosen arrival for that architecture.
14. Page table's outward-spiral cell "~1 km/s" at 2.5×10⁻⁴ not reproducible (engine: 0.0). *Fixed:*
    "≈0 km/s".
15. GTO drop-off quoted "7.6 → ~4.2 km/s" vs engine 7.67 → 4.03. *Fixed:* "~7.7 → ~4.0 km/s".
16. KPI corner case: pumped + solar + diverged mass fell through to a "non-solar" label with a
    0.0 sentinel shown as computed. *Fixed:* dedicated branch explains the sentinel.

### Raised but refuted (kept for the record)

- "Oberth language overstates the Δv economics" — arithmetically right (the pumped campaign costs
  more Δv than any impulsive alternative; the win is *power availability* under the 1/r² fade, which
  the page states), but not a repo defect. A clarifying sentence was added to the caveats anyway.
- "Feasibility badge shows the wrong reason" — the coarse badge is an algebraically consistent
  summary (every infeasibility is a below-the-floor condition); dedicated badges carry the specifics.

## Bottom line

The two manoeuvres survive adversarial re-derivation: the pumping mechanism, its design point, the
contiguous threshold edge, and the entire synchrotron recirculation model (including the two
corrections that kill naive equal-kick arithmetic) are all real and independently reproduced. What
the fleet caught was the *packaging*: a docstring describing the wrong policy, a threshold narrative
that hid genuine non-monotonicity, an α band whose low edge violated the mission's own rocket
equation, and a budget that silently dropped the plane change. All 19 confirmed findings are fixed
or explicitly documented as of build 126; guard checks were added so none can silently regress
(suite 90/90, parity 35/35, UI 78/78).

*Prompts for the parallel external audits (Codex/Grok/Gemini) are §11–12 of
`audit/AUDIT_PROMPTS.md`; their conclusions belong in `audit/codex|grok|gemini/` as before.*
