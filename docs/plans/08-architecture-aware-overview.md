# 08 — Architecture-aware overview & 2-D views

Issue: https://github.com/fermiexplorer/fermi/issues/8

## Problem

The chase cam draws the architecture-aware integrated model (`buildModel`),
but the overview 3-D panel and the 2-D panels still draw an
architecture-BLIND reference escape (one continuous tangential spiral to v∞
via `buildTraj`, rotated onto the AC asymptote). For the pumped, Jupiter,
Oberth and synchrotron architectures those panels therefore show a schematic
path the vehicle does not fly. This is disclosed in the Limitations bullet,
but the owner directive is "no fake renderings anywhere" — the disclosure
should become unnecessary.

## Change

Feed the overview 3-D (`chartOrbit3d`) and the 2-D panels (`follow2d`,
`chartOrbit2d`) from `buildModel`'s pos/time arrays (the same simplified
polylines the chase cam consumes), including the assist-body/burn-point
marker (Jupiter at 5.2 AU, synchrotron station, Oberth kick) added in build
171. Keep the log-distance scaling and the cruise splice conventions; retire
the `buildTraj` reference path from these views (it may remain as an internal
reference for the direct architecture's charts if anything still needs it).

## Verification

- Playwright checks per architecture: the overview path's maximum radius and
  event locations match the model (Jupiter 5.2 AU, station/kick radii);
  frame-rate and build-time budgets hold; no page errors.
- Full suite via tmp/ro/verify_ui_now.py.
- Remove/adjust the Limitations bullet describing the architecture-blind
  reference once the views are model-fed.

## Push / merge

One commit (view rewiring + checks + Limitations copy), release via
tools/release.py (deploy — index.html changes), close the issue with the
verification record.
