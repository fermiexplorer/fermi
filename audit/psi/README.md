# PSI external assessment — PSI‑TR‑2026‑0714

`PSI-TR-2026-0714.pdf` — *Interstellar Precursor Mission to Alpha Centauri: Technical
Feasibility Assessment*, Physical Superintelligence PBC, July 2026 (**working draft**),
produced and verified end-to-end by PSI's autonomous physics-research platform. Included
here with attribution as the independent external cross-assessment of this project.

## What it contributes

- **Confirms the geometry to <0.5%**: optimum 73,012 yr (ours 72,800), tilt 2.48° (2.4°),
  impulsive floor 13.85 km/s (13.88), tangential intercept 58,422 yr (58,138), closest
  approach 27,955 yr @ 3.15 ly (27,960 @ 3.13) — and all five of this project's
  arrival-time intuitions.
- **Source of the perihelion-pumping closure**: the outward-spiral power wall is a
  property of the trajectory class; a pumping trajectory at a₀ = 2.5×10⁻⁴ m/s² (today's
  hardware) reaches the full cruise. Their optimized 12-yr schedule costs Δv 23.97 km/s;
  certified heliocentric lower bound 16.56 km/s (unconstrained time, r_p ≥ 0.42 AU).
- **Departure accounting**: SEP total from LEO 30.5–31.6 km/s (7.6 escape + 22.9–24.0
  heliocentric); GTO drop-off 7.6 → 4.24 km/s closes a ~100 kg vehicle.
- **Independent target screening**: LSPM J2146+3813 best (their Bailer-Jones check,
  0.568 pc @ +82.5 kyr, matches our 1.86 ly @ +83 kyr), λ Ser best solar-type second,
  α² Lib excluded, catalogue sweep finds nothing better.

## Our cross-validation of it (engine + adversarial audits)

- Outward-spiral ceilings: ours 0 / 3.1 / 16.7 km/s vs theirs 0 / 3.4 / 17.0 at
  a₀ = 1.5/5/10×10⁻⁴ (their own two-integrator band is 2.7%).
- Pumping mechanism reproduced with an independent bang-bang policy
  (`fermi_sim.departure.perihelion_pumped_vinf`): 23.66 km/s at the design point,
  Δv 25.63 (theirs 23.97 optimized), 9.6 yr (theirs 12.0), 4.9 revolutions
  (2.13 retrograde pump-down + 3 perihelion passes + finisher; Δv split 8.3 retro +
  17.3 prograde). The +1.66 km/s premium of our policy is almost entirely in the cruder
  retrograde pump-down; the prograde legs agree to ~2%.
- Contiguous working-region edge a₀ ≈ 2.24×10⁻⁴ m/s² (validated by three independent
  integrators; success below is phasing-dependent and non-monotonic — see
  `audit/fable/fable-pumping-synchrotron-audit.md`).
- Their independent-model concurrence claims are consistent with our independent audits
  (astropy, GMAT, Codex/Grok/Gemini/Fable re-implementations).

Validated design profile adopted from this work: `fermi_sim.constants.PUMP_DESIGN_A0`
(2.5×10⁻⁴ m/s²) and `PUMP_DESIGN_ISP` (2800 s).
