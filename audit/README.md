# `audit/` — independent verification of the Fermi model

The Fermi engine (`fermi_sim/`) is the source of truth; the web calculator (`web/physics.js`) is
a parity-checked port of it. **Nothing here checks the engine against itself.** Every audit
re-derives the physics by a *different* method (astropy, conservation laws, brute-force
optimisation, a separate propagator, or an independent AI re-implementation) and compares.

**Start here → [`AUDIT_COMPARISON.md`](AUDIT_COMPARISON.md)** — every source side by side, which
results are trustworthy and which are single-sourced, and why the numbers differ where they do.

---

## Summary of latest results

| Audit | Source / method | Scope | Latest verdict | Agreement | Docs |
|---|---|---|---|---|---|
| **In-repo suite** | Python, different method than engine | ephemeris → power gate → pumping → synchrotron → data → docs | **130 / 130 pass** | exact | [`calcs/`](calcs/) |
| **Web parity** | Node, `web/physics.js` vs Python | every shared function incl. pumping | **35 / 35 pass** | ~13 sig figs | [`calcs/audit_webjs.mjs`](calcs/audit_webjs.mjs) |
| **UI behaviour** | Playwright slider sweep | every control drives the right output | **82 / 82 pass** | — | [`calcs/ui_sliders.py`](calcs/ui_sliders.py) |
| **NASA GMAT** | flight-proven propagator (separate codebase) | departure energetics | **PASS** | ≤ 0.01 % | [`gmat/`](gmat/) |
| **Codex** | hand vectors + rocket equation (v01–v04) | geometry, intercept, departure, xenon | verdict holds | ≤ 0.1 % | [`codex/`](codex/) |
| **Grok** | hand ephemeris + sensitivity sweeps | all 10 areas | verdict holds | ≤ 0.1 % | [`grok/`](grok/) |
| **Gemini** | astropy + scipy `solve_ivp` (RK45) | ephemeris, intercept, spiral | no disagreement | ≤ 0.1 % | [`gemini/`](gemini/) |
| **Fable — core** | scipy RK45 + finite-difference ephemeris | geometry → power gate (22 checks) | PASS | < 0.01 % | [`fable/fable-conclusions.md`](fable/fable-conclusions.md) |
| **Fable — pumping** | 2 independent integrators (RK4 + DOP853), 31 agents | perihelion pumping + synchrotron | mechanism confirmed; 19 packaging fixes | < 0.2 % | [`fable/fable-pumping-synchrotron-audit.md`](fable/fable-pumping-synchrotron-audit.md) |
| **Fable — text/coherence** | multi-agent adversarial (144 / 98 / 43 agents) | prose, data, default-state, envelope | ~180 findings fixed across builds | — | [`fable/fable-text-audit.md`](fable/fable-text-audit.md) |
| **PSI (external)** | autonomous physics-research platform | full mission | independent feasibility assessment | geometry < 0.5 % | [`psi/`](psi/) |
| **STK** | Ansys STK/Astrogator | departure cross-validation | **prep only** (needs a Windows STK trial) | — | [`stk/`](stk/) |

*Agreement* is vs the engine on headline quantities. The **triangulated tier** (geometry,
departure, power gate) is confirmed by four mutually-blind AI bots **plus** GMAT **plus** PSI —
none of which saw each other's work. See `AUDIT_COMPARISON.md` §1 for the independence chain.

---

## What each source can and cannot vouch for

- **Codex / Grok / Gemini / Fable-core / GMAT** ran on builds that *predate* perihelion pumping,
  so they vouch for the **geometry, intercept, and departure energetics only** — and they never
  saw the PSI report (it did not exist in the model yet). That makes them genuine independent
  corroboration of the same geometry PSI later confirmed.
- **Fable-pumping** vouches for the **pumping mechanism, endpoints, and thresholds**, re-derived
  from the policy spec with two integrators — it did not have the PSI PDF, only our reproduction.
- **PSI** is the **origin** of the pumping closure and an independent confirmation of our geometry;
  its optimised Δv is single-sourced (see `AUDIT_COMPARISON.md` §4).

## Directory map

```
AUDIT_COMPARISON.md   the cross-source comparison + trust analysis (read this first)
AUDIT_PROMPTS.md      adversarial prompts (§1–10 geometry/departure, §11–12 pumping/synchrotron)
calcs/                the in-repo independent suite (Python) + Node parity check
codex/ grok/          independent AI re-implementations + committed results
  gemini/ fable/
gmat/                 NASA GMAT cross-validation (scripts, comparison, raw outputs)
psi/                  archived external assessment PSI-TR-2026-0714 + our cross-validation notes
stk/                  Ansys STK/Astrogator prep (driver + comparator; awaits a trial licence)
```

## Adding a new independent audit

Follow the setup line in `AUDIT_PROMPTS.md`, re-derive by a method *different* from the engine,
commit your conclusions + a `*_results.json` under a new `audit/<name>/`, and add a row to the
table above and a column to `AUDIT_COMPARISON.md`.
