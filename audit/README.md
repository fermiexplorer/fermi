# `audit/` — independent verification of the Fermi model

The Fermi engine (`fermi_sim/`) is the source of truth; the web calculator (`web/physics.js`) is
a parity-checked port of it. **Nothing here checks the engine against itself.** Every audit
re-derives the physics by a *different* method (astropy, conservation laws, brute-force
optimisation, a separate propagator, or an independent AI re-implementation) and compares.

**Start here → [`AUDIT_COMPARISON.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md)**
— every source side by side, which results are trustworthy and which are single-sourced, why the
numbers differ where they do, and why the bang-bang gate's campaign is 4.9 revolutions while PSI's
is 12 *years* (different units — see §0 there). The flown default is the anchored optimised
THERMAL schedule, Δv 24.44 km/s at 12-yr custody; the PSI-comparable figure at their idealised 4×
cap is 23.14 km/s — 3.5% under PSI's published optimum.

> **The result the whole audit record supports:** the same vehicle needs **~100–140 W/kg** as an
> outward spiral but only **~15–21 W/kg** pumped — **~6×, from the trajectory alone, not the power
> system.** Decomposed (4× power availability × 2.2× Oberth leverage, minus the pump-down cost) and
> corroborated by engine, Fable and PSI in
> [§2c](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md#2c-the-6x-specific-power-result--the-trajectory-not-the-power-system-decides-feasibility).

---

## Summary of latest results

| Audit | Source / method | Scope | Latest verdict | Agreement | Docs |
|---|---|---|---|---|---|
| **In-repo suite** | Python, different method than engine | ephemeris → power gate → pumping/thermal → synchrotron → data → docs | **250 / 250 pass** | exact | [calcs/](https://github.com/fermiexplorer/fermi/tree/main/audit/calcs) · [run_audits.py](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/run_audits.py) |
| **Web parity** | Node, `web/physics.js` vs Python | every shared function incl. pumping + thermal + plane tax | **49 / 49 pass** | ~13 sig figs | [audit_webjs.mjs](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/audit_webjs.mjs) |
| **UI behaviour** | Playwright slider sweep | every control drives the right output (+ tabs, presets, native-default drift, design-epoch snap) | **93 / 93 pass** | — | [ui_sliders.py](https://github.com/fermiexplorer/fermi/blob/main/audit/calcs/ui_sliders.py) |
| **NASA GMAT** | flight-proven propagator (separate codebase) | departure energetics | **PASS** | ≤ 0.01 % | [README](https://github.com/fermiexplorer/fermi/blob/main/audit/gmat/README.md) · [scripts](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/scripts) · [outputs](https://github.com/fermiexplorer/fermi/tree/main/audit/gmat/out) |
| **Codex** | hand vectors + rocket equation (v01–v04) | geometry, intercept, departure, xenon | verdict holds | ≤ 0.1 % | [v04](https://github.com/fermiexplorer/fermi/blob/main/audit/codex/codex-conclusions-v04.md) · [all runs](https://github.com/fermiexplorer/fermi/tree/main/audit/codex) |
| **Grok** | hand ephemeris + sensitivity sweeps | all 10 areas | verdict holds | ≤ 0.1 % | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/grok-conclusions.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/grok/prompt_results.json) |
| **Gemini** | astropy + scipy `solve_ivp` (RK45) | ephemeris, intercept, spiral | no disagreement | ≤ 0.1 % | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini-conclusions.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/gemini/gemini_results.json) |
| **Fable — core** | scipy RK45 + finite-difference ephemeris | geometry → power gate (22 checks) | PASS | < 0.01 % | [conclusions](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-conclusions.md) · [results](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable_results.json) |
| **Fable — pumping** | 2 independent integrators (RK4 + DOP853), 31 agents | perihelion pumping + synchrotron | mechanism confirmed; 19 packaging fixes | < 0.2 % | [pumping/synchrotron audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-pumping-synchrotron-audit.md) |
| **Fable — text/coherence** | multi-agent adversarial (144 / 98 / 43 agents) | prose, data, default-state, envelope | ~180 findings fixed across builds | — | [text audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-text-audit.md) |
| **Fable — deep audit b154–167** | 227 agents: 10 finder lenses + 3 adversarial skeptics per finding | thermal model, optimised schedules, dual tax, JS ports, UI/tabs/presets, docs, audit-suite meta | 72 raw → 43 confirmed (0 critical) → all fixed/disclosed; 29 refuted | — | [deep audit](https://github.com/fermiexplorer/fermi/blob/main/audit/fable/fable-deep-audit-b154-167.md) |
| **PSI (external)** | autonomous physics-research platform | full mission | independent feasibility assessment | geometry < 0.5 % | [final, July 2026 (PDF)](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI_FermiExplorerInterstellarPrecursor_FeasibilityAssessment.pdf) · [working draft](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/PSI-TR-2026-0714.pdf) · [our notes](https://github.com/fermiexplorer/fermi/blob/main/audit/psi/README.md) |
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
  its 12-yr optimised Δv is now independently confirmed (and beaten by 3.5%) by our own
  optimised-schedule integrator (see
  [`AUDIT_COMPARISON.md` §4](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_COMPARISON.md#4-perihelion-pumping--the-narrower-chain-engine-psi-fable-adversarial-only)).

## Directory map

```
AUDIT_COMPARISON.md   the cross-source comparison + trust analysis (read this first)
EXTERNAL_AUDIT_SCOPE.md  scope & file guide for an independent auditor, human or AI (engine-focused; browser out of scope)
AUDIT_PROMPTS.md      adversarial prompts (§1–10 geometry/departure, §11–12 pumping/synchrotron)
calcs/                the in-repo independent suite (Python) + Node parity check
codex/ grok/          independent AI re-implementations + committed results
  gemini/ fable/
gmat/                 NASA GMAT cross-validation (scripts, comparison, raw outputs)
psi/                  archived external PSI assessments (final July 2026 + working draft) + our cross-validation notes and cross-check script
stk/                  Ansys STK/Astrogator prep (driver + comparator; awaits a trial licence)
```

## Guide for an independent auditor (human or AI)

Any independent reviewer — **human or AI** — should start with
[`EXTERNAL_AUDIT_SCOPE.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/EXTERNAL_AUDIT_SCOPE.md);
both review the same things. It is the file-by-file scope guide: what is in and out of scope
(browser code is excluded), the Tier-1 engine files and exactly what to check in each, the headline
numbers to reproduce by an independent method, the disclosed model assumptions, and the known
numerical limitations of the implementation — each stated with its magnitude and the case for why
it is immaterial at this precision, for you to verify.
AI reviewers additionally get the adversarial prompt set in
[`AUDIT_PROMPTS.md`](https://github.com/fermiexplorer/fermi/blob/main/audit/AUDIT_PROMPTS.md);
prior AI runs are under `codex/ grok/ gemini/ fable/`.

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
