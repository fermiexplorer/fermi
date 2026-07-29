# Deep adversarial multi-agent audit — builds 154–167

Method: 227 agents in a find → adversarially-verify → synthesize pipeline. Ten
finder lenses (thermal physics, pump-schedule integrator, departure/budget,
JS↔Python parity, compute()/UI logic, animation truth, doc coherence, a
meta-audit of the audit suite itself, numerical edge cases, UI regression +
star data), each required to back findings with measurements (probe scripts
written and run against the shipped code). Every finding was then judged by
three independent skeptic agents with distinct lenses (correctness /
reproduction / materiality), each instructed to refute; survival required 2 of
3 non-refutals, and most survivors were independently re-measured by the
skeptics. 3,162 tool calls, ~6 h wall clock.

**Result: 72 raw findings → 43 confirmed, 29 refuted. Zero critical findings —
no shipped headline number was wrong.** All 43 confirmed findings were fixed
or disclosed in the build that ships alongside this record; dispositions
below.

## Confirmed majors (13 unique) and their dispositions

| Finding | Disposition |
|---|---|
| Four index.html passages + AUDIT_COMPARISON + dropdown `selected` states still presented the far-term 1000 W/kg GaAs set as "the page default" after issue #7 | FIXED — all default prose re-baselined; dropdowns re-optioned and preset-synced |
| "Today's silicon" branding vs the GaAs-only thermal gate (silicon cells strand at the 0.42 AU floor per the project's own model) | FIXED — default rebranded "today's-class hardware: 91 W/kg array mass with GaAs-class cells"; a true silicon option remains with a strand warning |
| ⚙ Optimize solar grid started at 5 kW — "lightest feasible" wrong by ~2× (82.6 kg @1 kW existed) | FIXED — grid now starts at 1 kW |
| Anchor links inert after a tab switch when the hash already matched | FIXED — tab clicks clear the stale hash |
| Malformed hash (#%zz) threw in tabForHash, stacking all panes and killing the scroll guard | FIXED — decode wrapped, returns null |
| `failed` read dead in the buildModel loop-break; bound strands ran to the 500k-step cap (multi-second freeze) | FIXED — verdict assigned before the loop |
| Animation flew weak (un-throttled) pumped vehicles at ~1.29× the gated a₀ (thrust/massNow vs thrust/wet) | FIXED — drawn campaign uses the gate's a₀ |
| audit/README mislabelled the 23.14 km/s idealised-4× figure as "the flown default" (thermal 24.44 is) + stale suite counts | FIXED |
| Shipped default (thermal scheduled) campaign verified only by circular replay | FIXED — independence bridge added: the scheduled integrator with the BANG_BANG geometry must match the independently re-integrated bang-bang path (agrees 0.13% dv / 0.04% v∞) |
| pump_schedule.py comments overclaimed audit replay coverage; campaign tables had no replay guard | FIXED — comments state actual coverage; fresh-integration knot guards added for the thermal tax/campaign tables |
| Baked tables carry the engine dt's first-order truncation (~+8–35 m/s, conservative at the anchor) with "full resolution" wording | DISCLOSED — comments + EXTERNAL_AUDIT_SCOPE §8 entry; ≤0.11% of any budget, absorbed by 0.1 km/s prose rounding |
| Stale "558 stars cross inside 50 ly / 1 Myr" (current catalogue: 868) | FIXED |
| ui_sliders' native-load guard was drift-blind (checked feasibility only) | FIXED — native page value= attributes now compared to the suite's DEFAULTS dict |

## Confirmed minors/info (30) — all addressed

KPI copy (un-throttled a₀ shown as the integration a₀; stale bang-bang animation
description; 60-yr integration cap now labelled on stall displays), JS API
strictness (pumpTaxFor now mirrors Python's schedule names and throws on
unknowns; integrators reject ispS ≤ 0), `_dt_scale` and `campaign_at`
validation, sticky-tabbar scroll-margin (16 → 56 px), capture-phase mouseleave
disarm (now container-only), interaction captions unified to "click/tap to
enable, then drag/scroll", preset hint now names the direct preset's 4 kg/kW
engine swap, cellEff/dropdown coherence, Altair optimum epoch corrected
(138 → 189 kyr min-cruise), burnoutMassKg uses the tracked pumped mass,
docstring accuracy (thermal power_model documented; overshoot and mass-floor
caveats quantified), suite-count refresh with extended stale-count guards,
dead bisection floor recorded as intended.

## Notable refuted claims (29 — recorded so they are not re-litigated)

The skeptics killed, with measurements: a claimed JS/Python default
power-model parity break (intended API asymmetry — the page passes explicit
models), "thermal 1.6e-4 grid closure is a timeout" (reaches within stated
tolerance), "gate non-monotonic in payload" (the disclosed phasing
sensitivity), "nuclear preset strands pwrkw on return to solar" (chosen
design), "the thermal bisection check is not independent" (it is
solver-independent, which is what it claims), and a claimed +19.6% vs "~15%"
LEO wet-mass understatement (within the stated rounding).
