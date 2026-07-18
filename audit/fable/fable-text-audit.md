# Fable multi-agent deep audit — reader-facing text of index.html

**Trigger:** recurring "fixed station"-class sloppiness spotted in review. **Method:** 144 agents in a
two-phase workflow — six auditors, each sweeping every methodology section, control hint, KPI/badge
string, and infeasibility message through one lens (physics precision · internal consistency · every
number recomputed against the engine/data · terminology & definitions · grammar/typo/style · dynamic
UI strings across all architecture × power-source states), then an independent confirmation pass per
finding. **123 findings raised, 134 confirmed line-items after verification** (some split), of which
34 major. All fixed in build 130 except the explicitly deferred items below.

## The big clusters (all fixed)

1. **The Δv presentation gap** (found independently by five of six auditors). The methodology said the
   calculator's required Δv is the ~25 km/s closed-form spiral, while the live calculator adds a
   +5 km/s conservative heliocentric-leg offset plus pointing margins and displays ~30.1 — and the
   Departure-Δv KPI printed an equation whose terms sum to 25.0 with "= 30.09" as the result, labelled
   "Optimistic". Fixed everywhere: §1/§2/CONOPS/architecture table/pipeline/auditor guide now state
   spiral ≈25 + 5 offset ⇒ ≈30 displayed; the KPI derivation closes arithmetically line by line
   (spiral = 25.01, + 5.00 offset [direct] or − assist gain [Jupiter], + nav margins ⇒ total); the
   KPI description is architecture-aware and calls the direct budget what it is — conservative.
2. **CONOPS mixed three stale design generations** (500 vs 600 kg wet, 248 vs 344 kg xenon, 204 mN
   needing η 0.6 beside a stated η 0.5, ~1.1 yr firing matching neither). Rewritten to one labelled
   reference configuration (5 kW silicon, η 0.50, Isp 3000 s → 170 mN, ~600 kg wet, ~344 kg Xe,
   ~1.9 yr firing, ~0.03–0.07 milli-g, T/W ~3×10⁻⁵), explicitly distinguished from the live card's
   high-α defaults; dependent numbers (auditor-guide kWh, §5b thrust example, §3 wet/dry example)
   updated to match.
3. **Seven KPI panels printed the literal word "undefined"** in their INPUTS lines (missing IN-map
   keys). Keys added/fixed (kstruct, wkgsolar; stale 'pen' dropped; enginekg→ekw; dead mislabeled
   'areal' removed; "RTG=40 W/kg" → "reactor=", chart legend likewise).
4. **The failure badge always blamed the 23.3 km/s floor** even when the real cause was mass
   divergence, a pumping stall, or a slow synchrotron kick. Badge and spec-card header are now
   cause-keyed and can no longer contradict the summary; the mass-diverges message is fuel-cell-aware
   (raising Isp makes reactant divergence worse, so it no longer advises it), "raise the reactor
   power" no longer appears for fuel-cell designs, and sentinel 0.0 km/s values are labelled
   "n/a (mass diverges)" instead of shown as computed.
5. **Number normalisation**: one a₀ threshold (2.24×10⁻⁴) everywhere; "floor" reserved for the 23.3
   tangential minimum with 23.64 renamed the ~23.6 design cruise (Oberth table re-anchored to 23.3:
   burns 2.37/1.95/1.39/0.98/0.76); §1 table 23.79→23.71 and 24.0→24.02; LSPM cruise unified at
   8.7 km/s (was 6.7/7.7/8.7 in three places); α² Lib "~35×" → ~14×; √(18²+8²)"≈19.4" fixed via
   unrounded 17.6/8.4; the >150 km/s completeness bound corrected to ~95; "~86 ly completeness"
   → ~315 ly; "55 Python checks" → 90; 501-vs-5,600 RV overrides scoped; solar-escape α threshold
   aligned to the shipped mid-30s W/kg data; Altair's two contradictory prices reconciled with a
   cross-reference; Gliese 710 epoch 1,280 kyr; HD 176051A 53%/~63; λ Ser lifetime remaining-vs-total
   fixed; the "5 vs 24 km/s" floor formula gains its missing −1.2 spiral-fit constant.
6. **Frame/precision**: LEO hint's "heliocentric v∞" → v∞,E; the speeds-view tooltip's tilt
   attribution corrected; v∞,⊕/v∞,Earth unified to v∞,E; espiral caption ("~milli-g" → fraction of a
   milli-g, "scales with" → inversely, stale 0.7-yr removed); the reactor hint no longer claims
   nuclear is "the only pure-electric path"; "the fade always wins" above 27 km/s properly attributed
   to the page's fixed sizing; solar-Oberth 1-AU comparison condition (parabolic start) stated;
   Ross 248/Gliese 445 shared-predicate error fixed; run-on sentences split (synchrotron intro,
   α Lib, Beyond-AC); "Spiraling/unmodeled/civilization/captureable/naive" normalised to the page's
   British style; R☉ markup unified; the unattributed "perfect candidate" quotation unquoted;
   changelog residue ("now derived", "now uses", "now sweeps") removed.

## Deferred (documented, not fixed here)

- `tmp/ro/make_starmap_data.py` min-α interpolation across the v=0 flat (root cause of the 36-vs-40
  escape-threshold drift): needs a generator fix + table regeneration — follow-up work; the prose now
  matches the shipped data.
- Full curly/straight quote-mark normalisation across HTML + JS strings: cosmetic, high-churn.
- "⚙ Optimize system" button label kept in US spelling as a product label.
- CONOPS static numbers could be live-rendered from the current design like the spec card; the
  labelled-reference-configuration approach was chosen instead.

**Guards after the pass:** pytest 8/8, independent suite 90/90, web parity 35/35, UI sweep 78/78,
no JS errors.
