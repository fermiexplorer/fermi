# Project Fermi — feasibility report

*A first-order analysis for the Alpha Centauri precursor tender. All numbers are
produced by `run_analysis.py` and independently cross-checked in `audits/`.*

## The question

Send a small spacecraft **99% of the way to Alpha Centauri (≤ 2600 AU of it) within
100,000 years**, with a ≥1 kg payload, departing from LEO on ion propulsion, no
gravity assist required. Is it feasible, and what is the minimum spacecraft Δv?

## Short answer

**Yes, it is feasible** with today's technology: a ~500 kg solar-electric vehicle,
~40–50% xenon, leaving LEO with a ~20 km/s low-thrust budget, arriving in the
~70,000–80,000 year window — comfortably inside the 100,000-year requirement.
The concept as sketched (≈500 kg, mostly xenon, direct from LEO, flight-proven
electric-thruster-class hardware) holds up.

## 1. Where to aim, and the minimum Δv

A probe that has escaped the Sun coasts at its heliocentric excess velocity v∞. To
hit Alpha Centauri at arrival time T it needs `V_p(T) = A₀/T + V_ac` — aim at where
AC is now (shrinking with T) **plus** match AC's space velocity.

- **Minimum cruise speed** is the *tangential intercept* at **~58,000 yr**, where v∞
  equals AC's tangential speed, **23.3 km/s**. But AC sits 42° below the ecliptic with
  +11 km/s of out-of-plane motion, so that aim is tilted ~10° out of plane — and
  out-of-plane velocity can't be borrowed from Earth.
- AC's track **crosses the ecliptic at ~79,000 yr**, where departure is purely in-plane.
- **The departure-Δv minimum is ≈13.88 km/s at ≈72,800 yr** (tilted ~2.4° off the
  ecliptic). The Δv curve is extremely flat near this optimum, so the round-number
  **75,000 yr** arrival is practically the same point: its Δv is **13.886 km/s**, just
  **~10 m/s more** than the 72,800 yr optimum (13.875 km/s) — a 0.07% difference, far
  below the model's precision. (Note the units: the *total* budget is ~13.9 **km/s**;
  the 75k-vs-optimum *penalty* is ~10 **m/s**.) Your intuition was right: you trade a
  hair more cruise speed (23.8 vs 23.3 km/s) for a near-elimination of the plane-change
  penalty.

**Minimum spacecraft Δv from LEO (direct, no gravity assist):**

| Regime | Δv from LEO | Arrival |
|---|---|---|
| Impulsive floor (full Oberth, chemical-like) | **~14 km/s** | ~73,000 yr |
| Realistic low-thrust SEP (perigee-biased) | **~20 km/s** | ~73,000 yr |
| Naïve continuous ion spiral (worst case) | ~25 km/s | ~73,000 yr |

The ~14 km/s is a hard floor (an impulsive kick at LEO perigee captures the full
Oberth benefit). Ion is low-thrust and loses most of that benefit, which is why the
realistic figure is ~20 km/s. **The benchmarked 20 km/s is credible.** The profile:
launch to a LEO of convenience, thrust to escape and build v∞ ≈ 24 km/s aimed near
AC's ~73–75 kyr position, then coast for roughly 70,000–80,000 years.

Aiming much past ~80 kyr (or much before ~65 kyr) raises Δv — AC's geometry makes the
~70–80 kyr window the sweet spot, exactly as expected.

## 2. Does it work with electric propulsion + solar? — Yes

At Isp 3000 s, 20 km/s needs ~50% xenon (mass ratio ≈ 2.0); a 500 kg wet vehicle is
~250 kg xenon + ~250 kg dry. The burn draws ~5 kW from a ~33 kg solar array and lasts
~1 year, all within a few AU of the Sun — where solar power is strongest and the burn
is most effective. No exotic technology required.

## 3. Solar vs fuel cell vs hybrid — solar wins decisively

Electric propulsion needs electrical energy `E ≈ ½ m_p v_e²/η`, and **E grows with
Isp**. For 20 km/s this is ~50,000 kWh (~180 GJ).

- **Solar:** the Sun supplies that energy for free; the array masses ~tens of kg.
- **Fuel cell:** chemical reactants store only ~MJ/kg, so they'd mass **tens of tonnes**
  (mass-optimal Isp ~1350 s still needs ~28 t of consumables — ~1000× a solar array).
  Running the ion engine at **Isp 50,000 s makes it far worse** (~440 t of reactant),
  because energy scales with v_e. If the spent fuel-cell exhaust is itself used as
  propellant, its exhaust velocity is capped at `√(2η·e_chem)` ≈ 2.4 km/s — chemical-
  rocket class, not ion. **The wall is energy density, not exhaust velocity.**
- **Hybrid:** adds the fuel cell's mass penalty for no benefit, since the whole burn is
  done near the Sun. No value.

The only sun-independent power worth considering is nuclear/RTG (energy-dense), but
this mission doesn't need it — the burn is over within a few AU. **Use solar.**

## 4. Direct vs gravity-assist ("hops")

The mission only needs v∞ ≈ 24 km/s (Voyager-1 left at ~16.6). Options:

- **Direct from LEO (recommended):** simplest, no timing dependence on the planets,
  meets the 2029 schedule. ~20 km/s SEP budget.
- **Jupiter flyby:** can donate ~10–15 km/s, but only if Jupiter lies along the AC aim
  direction (rarely true on a fixed launch date) and adds ~6 years + complexity.
- **Solar Oberth (powered close perihelion):** hugely leveraged — a ~1–2 km/s burn at
  ~6 R_sun yields the full 24 km/s. Best route to *minimum onboard Δv*, but needs a
  heat shield and a way to drop perihelion. Worth it only for a cost-no-object,
  absolute-minimum-Δv variant.

## 5. Schedule, payload, cost

- **Payload:** a 1 kg / 1U slot is trivial within a ~250 kg dry bus.
- **Schedule:** rideshare to LEO is routine; launch before end-2029 is plausible.
- **Cost:** treated as a soft constraint here. A stripped-down, mostly-automated probe
  in the few-$M to ~$10M range is consistent with the architecture, dominated by the
  bus, the xenon, and the thrusters.

## Bottom line for the tender

Direct **solar-electric ion from LEO** is the right architecture: ~500 kg, ~20 km/s,
~40–50% xenon, ~70,000–80,000-year arrival aimed close to the ecliptic. Fuel cells
are a dead end (energy density). Gravity assists are optional Δv-savers, not
necessities.
