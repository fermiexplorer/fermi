# 06 — Tabbed top-level page layout

Issue: https://github.com/fermiexplorer/fermi/issues/6

## Problem

index.html is one continuous ~3,000-line document — live calculator, long
methodology, star atlas, beyond-AC narrative, audit record, auditor guide,
references — with no top-level structure. It reads long and crowded; a
first-time visitor cannot tell the tool from the research prose from the
reference material.

## Change (owner decision: tabbed single page, not sub-pages)

1. A top-level tab bar directly under the page header, four tabs:
   - **Calculator** (default): everything currently before the
     "How the numbers are computed" section (controls, KPIs, charts, views).
   - **Methodology**: sections 1–5b + Limitations + "How the calculator
     works" + "What is α" + perihelion pumping + synchrotron.
   - **Star atlas & beyond AC**: "Beyond Alpha Centauri" through the
     target-selection strategy (all four star tables).
   - **Verification**: "Audits & independent verification" + GMAT + the
     auditor guide + "Repository structure" + "References".
2. DOM: split the single `<section class="method">` into per-tab
   `<section class="method tabpane">` wrappers; MOVE the verification block
   (currently mid-methodology) and the repo/references tail into the
   Verification pane. No prose changes — structure only.
3. JS: tab switching (buttons set `.active`, panes toggle `display`), a
   `resize` dispatch on activation (Plotly safety), and HASH ROUTING: on load
   and on `hashchange`, find the hash target, activate the pane containing
   it, then scroll to it. Every published anchor keeps working
   (anchor-pinning rule, `docs/DOC_MAINTENANCE.md`).
4. CSS: sticky tab bar, mobile-friendly (horizontal scroll), active-tab
   accent consistent with the existing look.

## Out of scope

Prose edits, section renames (anchor ids must not change), sub-page splits.

## Verification

- `tmp/ro/verify_ui_now.py` green (audits + parity + syntax + pytest + UI).
- Screenshot sweep: all four tabs, 1400 px and 390 px widths.
- Deep-link check: `#pumping`, `#synchrotron`,
  `#guide-for-an-independent-human-auditor`, `#gmat`, `#what-is-alpha`,
  `#solar-oberth` each activate the right tab and scroll to the target.
- A durable UI guard: the tab bar exists, the calculator pane is default,
  and a cross-tab deep link activates its pane (added to the UI suite).

## Push / merge

Branch work as usual; one commit (DOM restructure + tab CSS/JS + UI-suite
guard), release via `tools/release.py` (deploy — index.html changes), poll
live, close issue #6 with the verification record.
