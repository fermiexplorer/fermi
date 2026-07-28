# 07 — Per-architecture default component sets

Issue: https://github.com/fermiexplorer/fermi/issues/7

## Problem

The component defaults (1000 W/kg far-term array, 4 kg/kW engine) are a legacy
of the pre-pumping era, when the direct outward spiral was the default
architecture and nothing closed below vehicle α ≈ 100 W/kg. The pumped default
architecture closes at today's components, so the far-term defaults produce a
15 kg dry / 50 kg wet vehicle that reads like a hardware claim (external
reader comment), and PSI's ~100–150 kg vehicles look inconsistent when they
are just a different technology point.

Measured (`tmp/ro/i8_default_sweep.py`, read-only): with PSI-like non-array
inputs the pumped architecture closes down to ~70 W/kg array under the
derived thermal power curve (PSI's 60 W/kg floor marginally fails — the
honest cost of the thermal derate vs their idealised 4× cap); the
today's-silicon set (91 W/kg, 6 kg/kW, Isp 3000, 2 kW) closes at 162 kg wet /
52 kg dry, a₀ = 4.2×10⁻⁴, vehicle α 38 W/kg.

## Change (owner decision: presets per architecture; silicon pumped default)

1. `ARCH_PRESETS` in index.html: component-slider sets per `ga` radio —
   pumped/jupiter/oberth/synchro = today's silicon (91 W/kg, 6 kg/kW, Isp
   3000, η 0.5, 2.5% tank, 2 kW); direct = far-term high-α (1000 W/kg,
   4 kg/kW — physics demands α ≳ 100 for the outward spiral). A
   `PWR_PRESETS.nuclear` set (5 kW, 40 W/kg reactor) loads on selecting the
   nuclear source. Selecting an architecture applies its preset (sliders stay
   freely adjustable afterwards); a hint notes the preset load.
2. HTML default `value=` attributes become the pumped silicon set (wkgsolar
   91, enginekg 6), so Home/Reset land on it.
3. Verify every preset × architecture combination closes (or is the
   documented teaching failure, e.g. fuel cell).

## Re-baseline (same commit — DOC_MAINTENANCE one pass)

- ui_sliders: DEFAULTS dict, native-load guard, the α-corner pin (~120 →
  ~35–40), feasibility wording, plus NEW guards: clicking an architecture
  radio loads its preset; default pumped vehicle ~162 kg wet pin.
- README "Reference vehicles"; the dry-mass KPI / FEASIBLE copy that
  references the far-term array as default.
- Summary/badge numbers update live (no static pins beyond the above).

## Verification

- `tmp/ro/verify_ui_now.py` green at the new baseline.
- A read-only preset matrix script measuring every architecture × preset
  closure (batched, one run).

## Push / merge

One commit (presets + HTML defaults + UI guards + doc re-baseline), release
via `tools/release.py` (deploy — index.html changes), poll live, close #7.
Follow-up per owner directive: a deep multi-agent adversarial audit after
this ships.
