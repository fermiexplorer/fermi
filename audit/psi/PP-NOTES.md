# The PSI final assessment, read PP-first

Source: `PSI_FermiExplorerInterstellarPrecursor_FeasibilityAssessment.pdf` — the
**final** report (July 2026, Status: Final), not the earlier PSI-TR-2026-0714 working
draft. This note extracts everything the final report establishes **for the
perihelion-pumped (PP) mission specifically** — the mission architecture — plus what
this project has extended, and what remains open. Cross-validation of the whole
report: `README.md` (this directory) + `crosscheck_final.py`.

## 1. What the final report establishes for PP

**Trajectory class (their §4, F3–F4).** The outward spiral saturates below the
23.38 km/s cruise floor at every flyable thrust level; PP defeats the wall: their
optimized 12-yr schedule buys the 23.64 km/s cruise for Δv 23.97 km/s at
a₀ = 2.5×10⁻⁴ m/s², final mass fraction 0.418, ~1.3 yr cumulative thrust, escape
~2043 for a 2029 launch. Certified bracket for the unconstrained-time optimum:
[16.56, 18.87] km/s (33–58 yr powered) — patience is worth ~4 km/s, and only the
12-yr class closes the mass budget. Pumping-feasibility floor a₀ ≳ 2.25×10⁻⁴
(matches our independently derived 2.24×10⁻⁴ edge).

**Power/thermal (their §4.6, sensitivity).** All their pumping results assume the
factor-of-4 perihelion power cap; halving it costs ~1.9 km/s and stretches custody to
15–20 yr. (Our derived thermal curve — cap_eff(0.42 AU) = 3.54 from the GaAs energy
balance — lands between their cap-4 and cap-3 rows at unchanged 12-yr custody, and is
what the calculator flies.) Repeated 0.42 AU passes need MESSENGER-class thermal
qualification — "established engineering... a cost and schedule item; it poses no
physics risk" — priced as a 1.4× multiplier on their integration-and-test line.
A 10–20% array degradation beyond budget erases the LEO-start margin (their §5.3) —
one of their two arguments for the GTO drop-off.

**Vehicle closure (their §5, F6).** From LEO, 100 kg misses closure by 1.0–2.8% of
wet mass everywhere in their reference interval (minimum closing wet 113.5–146 kg);
**from a GTO drop-off, 100 kg closes with +4.1 points of margin** (even 80 kg at
+1.9), survives a 30% thrust-acceleration stress at ~110 kg, and absorbs their
measured 0.58 km/s out-of-plane increment at both interval ends. **R1: procure the
GTO drop-off with a 100–110 kg vehicle.** Their component set: Isp 2800 s at η 0.55,
60 W/kg system-level array (×1.25 belt degradation for LEO, ×1.15 GTO), 6 kg/kW PPU,
12% tankage, 9 kg fixed (1 kg payload + 8 kg bus).

**Propulsion parts (their F5, R2).** The PP operating point sits on **demonstrated
gridded-ion hardware**: NSTAR's flight-documented TH3–TH4 throttle points
(0.91–1.02 kW, 2843–2942 s, η 0.527–0.554), with 30,352 h and 235 kg of xenon
single-string ground life demonstrated vs the mission's ~17–21 kh and 64–103 kg
need. No flown Hall thruster covers the point (tops out ~1650 s at this power).
Isp ≥ 2800 s is a LEO-start requirement; a 2400 s thruster closes from GTO.
**R2: start the gridded-ion qualification campaign at once — it paces an end-2029
launch.** This is the "availability of typical parts" case for PP in one paragraph.

**Targeting (their §6, F2).** Open-loop pass probability 0.982 under their stated
error budget (20,000-draw seeded MC + independent analytic propagation to 0.011%);
thrust-magnitude knowledge at burn cutoff dominates (doubling it → 0.858); no
terminal guidance, no course-correction propellant, out-of-contact cruise
consistent. Catalog systematic (~860 AU cross-track between the two published
astrometric solutions) held separate; mitigation = a pre-departure astrometric
re-reduction (~17 yr available).

**Cost (their §7, F8) — the criterion the owner set.** Median $15.7–16.6M vs the
$10M target; launch ($1.0–1.3M) and propulsion ($0.6–1.2M) UNDER-run their $3M
allocations; the entire gap is bus + IT&Q + operations + margin (~$12M vs $3M).
The dominant structural driver is **powered-flight custody** (~13 yr implied by the
12-yr schedule; their model prices ~4 yr at ~$1.2M/yr nominal and flags ops as a
lower bound). "The gap is programmatic. It is not physical." Path to $10M:
automation-first operations (the mission's stated loss-of-contact tolerance is a
cost-structural feature, their R3) + compressed bus/IT&Q practice (~40%).

**Verification of the negative (exhaustive text sweep).** Because 73,012/73,000
appears ~38 times in the final PDF, an exhaustive machine sweep of the extracted
text (all 63 pages, pypdf) checked whether any of them is a PP-specific epoch
derivation. Result: every occurrence is (a) the impulsive/departure-geometry
optimum and its blind re-derivation, or (b) design-point inheritance — p16 states
it verbatim: "caveats keep this report's design point at 73,012 years... those
schedules are planar: they exclude the cost of acquiring the out-of-plane tilt...
Whether the cruise-speed saving survives the tilt bill is an open question...
left as future work" — or (c) downstream reuse (dispersion aim epoch, timeline,
coast length, custody pricing). No 77–78k AC arrival appears anywhere (the only
78k numbers are LSPM J2146+3813's arrival — a different star — and Table 14 row
labels). Sharper still: PSI's own PLANAR pumped column bottoms near 65,000 yr
(23.49 km/s), not 73k — so 73k is not even their planar pumped minimum; it is
purely the impulsive design point carried through, and their p63 states that
settling the pumped epoch "requires a three-dimensional re-optimization across
the window" — the computation this project performed.

**Arrival epoch — what the final report does NOT establish for PP.** Their 73,012-yr
optimum is derived for the impulsive/Earth-relative departure only; the PP arrival
trade is explicitly left open (Table 14 caveat: the pumped column "is planar and
excludes the cost of acquiring the out-of-plane aim tilt"; §2.5 "unsettled...
future work"; R6 item 5). Settled by this project: per-epoch full-campaign 3-D
simulation (`tools/derive_epoch_table.py`) puts the PP fuel minimum in a flat
~75–79.3k basin (crossing +0.03 km/s = the design default; 73k +0.27; ≤~68k
unflyable). The 73–79.3k span is worth ~2.4 kg of xenon (~$25k) — epoch is a cost
non-driver; arriving ~6 kyr sooner at 73k is a legitimate preference, not a fuel
optimum.

## 2. What this project has extended beyond the final report (PP)

- Derived thermal power curve (cap_eff 3.54, not an assumed 4× step) — the flown
  pricing; their cap-sensitivity brackets it.
- Derived 3-D tilt-cost curve (quadratic near 0; 0.51 km/s @2.48°; their measured
  0.58 at 4× vs our cap-model 0.61 — 5% apart) — closes their §4.8 planar limitation.
- The PP arrival-epoch optimization (above) — closes their R6 item 5.
- 12-yr schedule optimisation: 23.14 km/s at their 4× assumption vs their 23.97
  (−3.5%); anchored thermal 24.44 flown.

## 3. What PP work remains open (candidate next issues)

1. **Cost layer / $10M optimizer** (owner criterion): PSI-anchored line items +
   custody-vs-ops-rate trade on our schedule frontier (24.83@10 yr ↔ 24.44@12 ↔
   28.2@4.9) + automation assumption + GTO option. The big levers are custody and
   automation, not epoch or xenon.
2. **GTO drop-off as the PP default start** (their R1): the calculator supports a
   GTO-like start but defaults to LEO 590 km; adopting R1 would change the default
   budget (7.7 → ~4.0 km/s escape leg) and vehicle. Owner decision.
3. Thrust-magnitude calibration + dispersion surfacing (their R6 items 1–2) — not
   modeled on the page.
4. Bound-phase 3-D steering (>4° tilt validity) and off-design-a₀ tax tables —
   engine residuals, disclosed.
