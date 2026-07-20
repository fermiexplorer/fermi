# `audit/` — independent verification of the Fermi model

The Fermi engine (`fermi_sim/`) is the source of truth; the web calculator (`web/physics.js`) is
a parity-checked port of it. **Nothing here checks the engine against itself.** Every audit
re-derives the physics by a *different* method (astropy, conservation laws, brute-force
optimisation, a separate propagator, or an independent AI re-implementation) and compares.

**Start here → [`AUDIT_COMPARISON.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md)**
— every source side by side, which results are trustworthy and which are single-sourced, why the
numbers differ where they do, and why our pumping campaign is 4.9 revolutions while PSI's is 12
*years* (different units — see §0 there).

> **The result the whole audit record supports:** the same vehicle needs **~100–140 W/kg** as an
> outward spiral but only **~15–21 W/kg** pumped — **~6×, from the trajectory alone, not the power
> system.** Decomposed (4× power availability × 2.2× Oberth leverage, minus the pump-down cost) and
> corroborated by engine, Fable and PSI in
> [§2c](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md#2c-the-6x-specific-power-result--the-trajectory-not-the-power-system-decides-feasibility).

---

## Summary of latest results

| Audit | Source / method | Scope | Latest verdict | Agreement | Docs |
|---|---|---|---|---|---|
| **In-repo suite** | Python, different method than engine | ephemeris → power gate → pumping → synchrotron → data → docs | **130 / 130 pass** | exact | [calcs/](https://github.com/fermiexplorer/fermi/tree/main/audit/calcs) · [run_audits.py](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/run_audits.py) |
| **Web parity** | Node, `web/physics.js` vs Python | every shared function incl. pumping | **35 / 35 pass** | ~13 sig figs | [audit_webjs.mjs](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/audit_webjs.mjs) |
| **UI behaviour** | Playwright slider sweep | every control drives the right output | **82 / 82 pass** | — | [ui_sliders.py](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/ui_sliders.py) |
| **NASA GMAT** | flight-proven propagator (separate codebase) | departure energetics | **PASS** | ≤ 0.01 % | [README](https://github.com/fermiexplorer/fermi/blob/main/audit/gmat/README.md) · [scripts](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/scripts) · [outputs](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/out) |
| **Codex** | hand vectors + rocket equation (v01–v04) | geometry, intercept, departure, xenon | verdict holds | ≤ 0.1 % | [v04](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v04.md) · [all runs](https://github.com/fermiexplorer/fermi/tree/main/audit/codex) |
| **Grok** | hand ephemeris + sensitivity sweeps | all 10 areas | verdict holds | ≤ 0.1 % | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/grok-conclusions.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/prompt_results.json) |
| **Gemini** | astropy + scipy `solve_ivp` (RK45) | ephemeris, intercept, spiral | no disagreement | ≤ 0.1 % | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini-conclusions.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini_results.json) |
| **Fable — core** | scipy RK45 + finite-difference ephemeris | geometry → power gate (22 checks) | PASS | < 0.01 % | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-conclusions.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable_results.json) |
| **Fable — pumping** | 2 independent integrators (RK4 + DOP853), 31 agents | perihelion pumping + synchrotron | mechanism confirmed; 19 packaging fixes | < 0.2 % | [pumping/synchrotron audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-pumping-synchrotron-audit.md) |
| **Fable — text/coherence** | multi-agent adversarial (144 / 98 / 43 agents) | prose, data, default-state, envelope | ~180 findings fixed across builds | — | [text audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-text-audit.md) |
| **PSI (external)** | autonomous physics-research platform | full mission | independent feasibility assessment | geometry < 0.5 % | [PSI‑TR‑2026‑0714 (PDF)](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI-TR-2026-0714.pdf) · [our notes](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/README.md) |
| **STK** | Ansys STK/Astrogator | departure cross-validation | **prep only** (needs a Windows STK trial) | — | [stk/](https://github.com/fermiexplorer/fermi/tree/main/audit/stk) |

*Agreement* is vs the engine on headline quantities. The **triangulated tier** (geometry,
departure, power gate) is confirmed by four mutually-blind AI bots **plus** GMAT **plus** PSI —
none of which saw each other's work. See
[`AUDIT_COMPARISON.md` §1](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md#1-provenance--independence--what-each-source-was-given-and-whether-it-saw-psi)
for the independence chain.

---

## What each source can and cannot vouch for

- **Codex / Grok / Gemini / Fable-core / GMAT** ran on builds that *predate* perihelion pumping,
  so they vouch for the **geometry, intercept, and departure energetics only** — and they never
  saw the PSI report (it did not exist in the model yet). That makes them genuine independent
  corroboration of the same geometry PSI later confirmed.
- **Fable-pumping** vouches for the **pumping mechanism, endpoints, and thresholds**, re-derived
  from the policy spec with two integrators — it did not have the PSI PDF, only our reproduction.
- **PSI** is the **origin** of the pumping closure and an independent confirmation of our geometry;
  its optimised Δv is single-sourced (see
  [`AUDIT_COMPARISON.md` §4](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md#4-perihelion-pumping--the-narrower-chain-engine-psi-fable-adversarial-only)).

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

Follow the setup line in
[`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md),
re-derive by a method *different* from the engine, commit your conclusions + a `*_results.json`
under a new `audit/<name>/`, and add a row to the table above and a column to
[`AUDIT_COMPARISON.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md).

**Engine side, for reference:**
[`fermi_sim/`](https://github.com/fermiexplorer/fermi/tree/main/fermi_sim) ·
[`web/physics.js`](https://github.com/fermiexplorer/fermi/blob/main/web/physics.js) ·
[`run_analysis.py`](https://github.com/fermiexplorer/fermi/blob/main/run_analysis.py) ·
[`index.html`](https://github.com/fermiexplorer/fermi/blob/main/index.html) ·
[`docs/REPORT.md`](https://github.com/fermiexplorer/fermi/blob/main/docs/REPORT.md)
