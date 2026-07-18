# Fermi Explorer — Alpha Centauri ion-propulsion mission feasibility

A first-order ("Fermi") simulation and interactive calculator for an interstellar
precursor mission: get a small spacecraft **99% of the way to Alpha Centauri
(≤ 2600 AU) within 100,000 years**, carrying a ≥1 kg payload, departing from LEO
with ion propulsion.

> ⚠️ **PRELIMINARY — first-order "Fermi estimate" only.** Every number here is an
> order-of-magnitude sizing built on simplifying assumptions (straight-line target
> motion, patched-conic departure, additive low-thrust penalty, geometric
> gravity-assist bounds). It is intended for feasibility and architecture trades,
> **not** design or flight decisions, and **requires independent engineering
> validation** before being relied upon.

**Live calculator:** <https://fermiexplorer.github.io/>

It answers:

- Is the mission feasible with pure solar-electric ion propulsion? **Yes — via
  perihelion pumping at today's hardware** (PSI‑TR‑2026‑0714, archived in
  `audit/psi/`; the naive outward spiral does *not* close at today's α — the
  original ≈500 kg / ~20 km/s direct concept survives only as the outward-spiral
  reference case, power-gated at α ≳ 100 W/kg).
- What is the **minimum spacecraft Δv from LEO** with no gravity assist, and the
  mission profile that achieves it?
- **Solar vs fuel-cell vs hybrid** power — which wins, and why?
- **Direct vs pumped vs synchrotron vs gravity-assist** trajectories.

## Headline results

| Quantity | Value |
|---|---|
| Required heliocentric cruise speed v∞ | ~23–24 km/s |
| Min departure Δv from LEO (impulsive floor) | ~14 km/s @ ~73,000 yr arrival |
| Direct SEP departure Δv (conservative model) | ~25 km/s spiral + 5 km/s offset ≈ ~30 km/s |
| **Pumped SEP departure Δv (default architecture)** | ~31–34 km/s two-leg total; closes at today's α (~15–21 W/kg) |
| Best departure window | direct optimum ~72,800 yr; pumped optimum at the ~79,250 yr ecliptic crossing |
| Departure aim | ~2.4° off the ecliptic (direct optimum); 0° at the crossing |
| Reference vehicles | pumped default ~54 kg wet @2 kW GaAs; conservative direct ~600 kg wet @5 kW silicon |
| Power verdict | **Solar wins; fuel cells lose by ~1000×** (chemical energy too sparse) |

The transit time is set by cruise speed, not by the propulsion — the years-long burn
is negligible against the ~80,000-year coast.

## Layout

```
fermi_sim/            Python engine (source of truth)
  astro.py        Alpha Centauri ephemeris + ecliptic transform
  intercept.py    V_p = A0/T + V_ac geometry, arrival-time optimisation
  departure.py    LEO -> v_inf Δv (impulsive + numerical low-thrust spiral)
  spacecraft.py   rocket eq, power, solar vs fuel-cell mass models
  trajectory.py   cruise time, Jupiter assist, solar Oberth
run_analysis.py   prints the full integrated analysis
index.html        interactive calculator (sliders, live 3D/2D trajectory
                  animation, CONOPS, methodology, references)
web/physics.js    shared JS physics used by the page (parity-checked vs Python)
audit/calcs/      independent verification suite (Python + Node parity)
audit/codex/      Codex independent audit (conclusions + scripts)
audit/grok/       Grok independent audit (conclusions + scripts)
audit/gemini/     Gemini independent audit (astropy + scipy solve_ivp)
audit/fable/      Fable 5 independent audit (finite-difference ephemeris, RK45 re-integrations)
audit/gmat/       NASA GMAT cross-validation (mission scripts + install/run/compare + raw outputs)
audit/stk/        Ansys STK/Astrogator cross-validation (prep — driver + comparator; needs a Windows STK trial to run)
audit/AUDIT_PROMPTS.md  adversarial audit prompts
docs/             REPORT.md (tender report), plans/
```

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install numpy scipy astropy

# integrated numeric analysis
.venv/bin/python run_analysis.py

# independent audits (90 checks: astropy ephemeris, conservation laws, optima)
.venv/bin/python audit/calcs/run_audits.py

# web<->python parity (Node, 35 checks)
node audit/calcs/audit_webjs.mjs

# UI behaviour: every slider drives the right outputs, in the right direction (80 checks)
.venv/bin/python audit/calcs/ui_sliders.py

# NASA GMAT cross-validation of the departure model (downloads GMAT; Linux/WSL)
cd audit/gmat && ./install_gmat.sh && ./run_gmat.sh

# the interactive calculator (needs internet for the Plotly CDN)
python3 -m http.server 8000
# then open http://localhost:8000/index.html
```

## Verification

The physics is checked **independently** (different method, not self-comparison):

- ephemeris vs **astropy**; closest approach reproduced (~28 kyr, ~3 ly);
- intercept optimum vs **brute-force** optimiser + forward-propagation loop closure;
- departure Δv via **energy conservation**; spiral integrator convergence;
- rocket equation by **numerical mass-flow integration**;
- fuel-cell optimum Isp by **independent minimisation**;
- web JS vs Python **parity** (`audit/calcs/audit_webjs.mjs`);
- departure energetics vs **NASA GMAT** — the General Mission Analysis Tool, an
  independent flight-proven propagator from NASA Goddard. GMAT reproduces the impulsive
  departure C3 to 2×10⁻⁶ % and the low-thrust Earth-escape spiral time to 0.007 %
  (`audit/gmat/`; scripts, comparison and raw GMAT outputs are committed for inspection).

All 90 Python checks + 35 JS-parity checks pass (plus a Playwright UI render test, the
NASA GMAT cross-validation, and independent Codex, Grok, Gemini & Fable re-implementations
under `audit/`, which agree to ≤0.2% on every headline number). See
`audit/AUDIT_PROMPTS.md` for adversarial review prompts.

## Scope / limitations

First-order model: straight-line AC motion, patched-conic departure with best-case
launch timing, additive low-thrust penalty, geometric (not phased) gravity-assist
bounds. Cost is treated as a soft constraint and is out of scope here. Intended for
feasibility and architecture trades, not detailed trajectory design.

## License

MIT — see [LICENSE](LICENSE).
