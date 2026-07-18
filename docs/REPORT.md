# Project Fermi — feasibility report

*A first-order analysis for the Alpha Centauri precursor tender. All numbers are
produced by `run_analysis.py` and independently cross-checked in `audit/`: four parallel
model re-implementations — **Codex, Grok, Gemini and Fable**
(`audit/codex|grok|gemini|fable/`) — agree with the engine on every headline quantity to
≤0.2 %, and a [NASA GMAT](https://gmat.gsfc.nasa.gov/) cross-validation of the departure
energetics (`audit/gmat/`) reproduces the impulsive-departure C3 and the low-thrust
Earth-escape spiral time to within 0.01 %.*

## The question

Send a small spacecraft **99% of the way to Alpha Centauri (≤ 2600 AU of it) within
100,000 years**, with a ≥1 kg payload, departing from LEO on ion propulsion. Is it
feasible, and what is the minimum spacecraft Δv?

## Short answer

**Yes — but the conservative case is decisive, and it rules out the obvious choice.**
The geometry is comfortable (a ~24 km/s cruise reaches AC in the ~70,000–80,000-yr
window, well inside 100,000 yr). The catch is *building* that 24 km/s with electric
propulsion: a **pure solar-electric** probe is **power-limited** — as it spirals out,
array power falls as 1/r², its thrust starves, and the achievable cruise speed
**saturates below the 23.4 km/s floor**. So pure solar-electric **does not close from
LEO**. Three architectures do:

1. **Nuclear-electric ion** — constant power (no 1/r² fade); the only *pure-electric*
   path that closes. ~5 kW fission reactor + gridded ion → ~24.8 km/s, mass closes.
2. **Solar-Oberth** — a ~1.4 km/s burn at a close perihelion yields the full 24 km/s,
   but needs a chemical kick stage, a heat shield, and a gravity-assist tour to set up.
3. **Chemical kick from LEO** — ~14 km/s impulsive does the whole job (the classic floor).

The recommended closing architecture is **nuclear-electric ion**: it keeps the
simplicity of a direct, inertial aim (no planetary alignment, no heat shield) and is the
only option that closes on electric propulsion alone.

## 1. Where to aim, and the cruise floor

A probe that has escaped the Sun coasts at its heliocentric excess velocity v∞. To hit
Alpha Centauri at arrival time T it needs `V_p(T) = A₀/T + V_ac` — aim at where AC is now
(shrinking with T) **plus** match AC's space velocity.

- **Minimum cruise speed** is the *tangential intercept* at **~58,000 yr**, where v∞
  equals AC's tangential speed, **23.3 km/s** — a hard floor (you cannot intercept any
  slower). AC sits 42° below the ecliptic with +11 km/s of out-of-plane motion, so that
  aim is tilted ~10° out of plane, and out-of-plane velocity can't be borrowed from Earth.
- AC's track **crosses the ecliptic at ~79,000 yr**, where departure is purely in-plane.
- **The departure-Δv minimum is at ≈72,800 yr** (tilted ~2.4° off the ecliptic). The Δv
  curve is very flat near this optimum, so the round-number **75,000 yr** arrival is
  practically the same point.

So the cruise floor is **v∞ ≈ 23.4 km/s** and the natural arrival is **~73,000–75,000 yr** —
comfortably inside the 100,000-yr requirement. *This geometry is robust; the feasibility
question is entirely about how you build the 24 km/s.*

> **Δv budget vs cruise speed (a common confusion).** A departure Δv from LEO is **not**
> the cruise speed. An impulsive ~14 km/s LEO kick becomes a **~24 km/s heliocentric
> cruise** via (a) the Oberth effect at LEO perigee and (b) inheriting Earth's 29.8 km/s
> orbital velocity. The check closes: AC recedes to ~6.0 ly by 75,000 yr, and
> 23.8 km/s × 75,000 yr ≈ 6.0 ly — exactly AC's distance then.

> **Update (July 2026).** The outward-spiral power wall below is a property of the
> *trajectory class*, not of solar power: **multi-revolution perihelion pumping** (drop
> perihelion to 0.42 AU, burn at perihelion where power is up to 4× the 1-AU rating)
> reaches the full cruise speed at today's vehicle α (~15–21 W/kg), no reactor or assist
> required. The mechanism and its a₀ ≈ 2.25×10⁻⁴ m/s² failure threshold are integrated in
> the engine (`perihelion_pumped_vinf`) and cross-checked externally. The α ≳ 100 W/kg
> condition below therefore applies to the outward-spiral class only. The full SEP total
> from LEO is ~30–32 km/s (7.6 km/s Earth escape + ~23–24 heliocentric); a GTO drop-off
> cuts the Earth leg to ~4.2 km/s and closes a ~100 kg vehicle. See the live page's
> "Perihelion pumping" section.

## 2. The conservative power gate — pure solar closes only as a light (high-α) vehicle

Electric propulsion converts electrical power to thrust: `F = 2ηP/v_e`. For **solar**
EP, the array power scales as **1/r²**, so as the probe climbs away from the Sun its
thrust collapses. Integrating the heliocentric spiral with that fade (engine function
`sep_achievable_vinf`, 1/r² thrust, RK4) shows the achievable cruise v∞ **saturates** —
extra propellant burnt far out adds almost nothing:

| Power source | 5 kW | 10 kW | 20 kW |
|---|---|---|---|
| **Solar (1/r² fade)** | 0.0 km/s | 0.0 km/s | 14.4 km/s |
| **Required floor** | — 23.4 km/s — | | |

At *conservative* specific masses those designs land **below the 23.4 km/s floor** — but the
binding variable is **not power, it is the whole-vehicle specific power α = power ÷ dry mass**.
More kilowatts don't help (a bigger array just scales the probe at the same α); what matters is
how light the *whole* vehicle is.

### 2b. The high-α corner — where solar DOES close
A light enough vehicle has a **short burn (~0.3 yr) near 1 AU**, so the 1/r² fade barely bites and
the achievable v∞ approaches the impulsive-from-1-AU limit (~38 km/s). The feasibility frontier is:

| Vehicle α (W/kg) | Achievable v∞ | |
|---|---|---|
| ~60 | ~5 km/s | ✗ |
| **~100** | **~24 km/s** | **← threshold** |
| ~155 | 37 km/s | ✓ |
| ~200 | 38 km/s (saturates) | ✓ |

So **pure solar-electric closes above α ≈ 100 W/kg.** The **recommended (default) high-α point uses
ultra-thin GaAs** (~1000 W/kg array — Alta-Devices-class epitaxial-liftoff cells, demonstrated at cell
level; lightweight blanket is the far-term step) paired with a **near-term ~4 kg/kW thruster** → α ≈
130, v∞ ≈ 30 km/s, ~40 kg wet. Crucially the 1000 W/kg array makes the array the demonstrated lever and
relaxes the thruster to ~4–5 kg/kW (close to today's ~6) — a *single* far-term stretch rather than two.
Optimal Isp ≈ 2800–3500 s; feasibility is power-independent (2 kW → 40 kg probe, 20 kW → larger, same α).

### 2c. Feasibility frontier & the tech-maturity trade
The two α levers (array W/kg, thruster kg/kW) trade along the closing contour — and crucially you
**cannot** close with today's ~6 kg/kW thruster (it would need a ~2000 W/kg array); the thruster
must improve:

| Thruster kg/kW | Array W/kg needed to close | stretch vs today |
|---|---|---|
| 2 | 238 | 1.6× array, 3× thruster |
| **3** | **313** | **2.1× array, 2× thruster** (the default's neighborhood) |
| 4 | 455 | 3.0× array, 1.5× thruster |
| 6 (today) | ~2000 | 13× array — impractical |

**Nuclear-vs-solar maturity trade.** High-α solar needs **two ~2–3× stretches** (≈2.7× array over
ROSA's 150 W/kg, ≈2× lighter thruster than Hall's 6 kg/kW) — both on a continuous commercial roadmap
(thin-film arrays, advanced gridded thrusters), and **no reactor, no gravity assist**. Nuclear-electric
needs **one ~7× stretch** (40 W/kg reactor vs Kilopower's ~6) *plus* the programmatic weight of flying a
fission reactor — a step-change, not a roadmap. On technology maturity the **high-α solar path is the
more conservative route to "feasible," which is why it is the default**; nuclear-electric remains the
no-far-term-array fallback. (This is the optimistic mirror: solar at high α ~150 W/kg, nuclear at low
α ~23 W/kg.) Today's silicon + Hall (α ~20–30) still does **not** close — α ≈ 100 W/kg is the bar.

## 3. The pure-electric closure — nuclear-electric ion

The fix is to remove the 1/r² fade. A **nuclear-electric reactor delivers constant
power**, so the spiral keeps thrusting all the way out and reaches the floor. The closing
design:

| Parameter | Value |
|---|---|
| Power | ~5 kW fission reactor @ ~40 W/kg (Kilopower→JIMO class) |
| Thruster | gridded ion, Isp ~3000 s |
| Achievable v∞ | **~24.8 km/s ≥ 23.4 floor ✓** |
| Xenon fraction | ~64% |
| Dry-bus margin | ~+64 kg (mass closes) |

It's a genuinely narrow corner: achievable v∞ *rises* with power (a higher
thrust-to-gravity ratio escapes more efficiently — 1 kW → ~18 km/s, 3 kW → ~23 km/s,
5 kW → ~25 km/s), but the reactor gets heavier, so the closure lives near ~5 kW. It needs
**both** nuclear-electric power **and** a high-Isp gridded thruster — an honest
"closes with advanced-but-credible hardware" result, not a comfortable margin.

**An RTG does not help.** It is the right *kind* of power (constant, no fade) but the
wrong *scale*: RTGs realistically top out near 0.5–1 kW (→ only ~15–18 km/s, short of the
floor regardless of mass) and mass ~5 W/kg (8× a reactor), so a hypothetical 5 kW RTG
would mass ~1000 kg on a ~256 kg bus. The closure needs a multi-kW **reactor**.

## 4. The fuel-cell energy wall — still a dead end

EP energy scales with `v_e` (`E ≈ ½ m_p v_e²/η`); for ~24 km/s this is ~50,000 kWh.

- **Solar** supplies that energy for free near the Sun; the array masses tens of kg — but
  it fades with 1/r² (§2), so it can't finish the heliocentric build.
- **Fuel cell:** chemical reactants store only ~MJ/kg → **tens of tonnes** of consumables
  (mass-optimal Isp ~1350 s still needs ~28 t). Using spent exhaust as propellant caps
  v_e at √(2η·e_chem) ≈ 2.4 km/s — chemical-rocket class. **The wall is energy density.**
- **Hybrid** adds the fuel-cell penalty for no benefit.

**Conclusion: deep-space EP power must be solar (near the Sun) or a nuclear-electric
reactor — fuel cells lose by ~3 orders of magnitude, and a low-power RTG can't supply the kW.**

## 5. The other closing routes — solar-Oberth and a chemical kick

### Solar-Oberth (powered close perihelion)

Diving to a small perihelion makes the spacecraft enormously fast; a burn there buys
disproportionate energy (Oberth: Δv at speed v adds ≈ v·Δv of specific energy).

| Perihelion | Speed | Burn to reach 23.4 km/s | Sunward-face temp |
|---|---|---|---|
| 20 R☉ | 138 km/s | 1.97 km/s | ~1300 K |
| **10 R☉** (Parker-class) | **195 km/s** | **1.40 km/s** | **~1830 K** |
| 5 R☉ | 276 km/s | 0.99 km/s | ~2600 K |

Buying the same 23.4 km/s at 1 AU costs ~6 km/s, so **10 R☉ gives ~4.3× leverage**. But
three caveats make it an *assist-staged, heat-shielded, chemical-at-perihelion*
architecture — it **sidesteps** the power wall rather than solving it:

1. **The perihelion burn must be chemical/high-thrust.** The Oberth benefit lasts only the
   hours-long perihelion pass; a ~0.2 N ion thruster would need ~58 days. So this is *not*
   a pure-electric path.
2. **Thermal limit ≈ 10 R☉.** ~1830 K needs a Parker Solar Probe-class carbon heat shield;
   diving deeper (3–5 R☉) shrinks the burn but pushes 2600–3350 K, beyond demonstrated shields.
3. **Getting there is the expensive leg.** Dropping perihelion to ~10 R☉ means shedding
   almost all of Earth's 29.8 km/s of angular momentum — a Jupiter gravity assist or a
   multi-year Venus-assist tour (Parker used seven). The 1.4 km/s headline burn is the easy part.

### Chemical kick from LEO

A high-thrust kick at LEO perigee captures the full Oberth benefit. To reach the floor by
**chemistry alone** takes **~14 km/s** from LEO (then a ~1-yr ion top-up is optional). But
there is **no cheap small-kick shortcut**: a ~3.7 km/s kick barely clears Earth's sphere of
influence (~3.5 km/s Earth-relative excess) and leaves the probe **still bound to the Sun**
(heliocentric v∞ ≈ 0). Because v∞ adds in quadrature, topping up a power-limited solar-EP
stage (~19.5 km/s) to the floor still needs ~13 km/s of v∞ from the kick ≈ a **~10 km/s**
burn. A small chemical kick contributes essentially nothing.

### Jupiter gravity assist

Can donate ~10–15 km/s of the heliocentric requirement, but only if Jupiter lies along the
AC aim direction (rarely true on a fixed launch date) and adds ~6 yr of cruise. An
opportunistic Δv-saver, not a baseline.

## 6. Schedule, payload, cost

- **Payload:** a 1 kg / 1U slot is trivial within a ~256 kg dry bus.
- **Schedule:** rideshare to LEO is routine. The nuclear-electric closure adds reactor
  development/qualification and launch-safety review — the schedule driver, not the bus.
- **Cost:** the reactor dominates a nuclear-electric variant; a solar-Oberth variant trades
  that for a heat shield + kick stage + a multi-year assist tour.

## Bottom line for the tender

The geometry closes easily; the **power physics** is the real constraint, and it reduces to
one number — the whole-vehicle specific power **α = power ÷ dry mass**. At conservative,
today's specific masses (α ~20–30 W/kg) **pure solar-electric does not close** (the 1/r² fade
saturates the cruise speed below the 23.4 km/s floor). Three architectures do close:

1. **Nuclear-electric ion** — constant power (no fade); closes at low α (~23 W/kg) with
   near-term specific masses but an optimistic ~40 W/kg reactor. The recommended baseline.
2. **High-α solar-electric** — pure solar *does* close above **α ≈ 100 W/kg**: an ultralight
   ~40 kg micro-probe (ultra-thin GaAs ~1000 W/kg array + ~4 kg/kW thruster, Isp ~3000 s) burns briefly near
   1 AU and dodges the fade. Needs far-term array + thruster tech, but no reactor and no assist.
3. **Solar-Oberth** (tiny burn, but heat shield + chemical kick + assist tour) or a **~14 km/s
   chemical kick** — the assist/kick routes.

Fuel cells remain a dead end; a low-power RTG cannot supply the needed kilowatts. Arrival
~73,000–75,000 yr (or ~80,000 yr at the ecliptic crossing for the lowest plane-change penalty),
aimed close to the ecliptic. **Optimizing feasibility = maximizing α** (light array + light
thruster + small structure/tank/payload, Isp ~3000 s); power then just sets the probe size.
