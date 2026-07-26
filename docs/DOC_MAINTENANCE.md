# Doc maintenance — how a change propagates across the .md files

The project's prose lives on **multiple surfaces that mirror each other**. Most
documentation pain comes from editing one surface and forgetting its mirrors.
This file is the map: for any change, find its cluster below, update **every**
file in the cluster **in one pass**, then run the guards.

## The one-pass rule

1. **Grep first.** Before editing, find every surface that states the fact
   (`grep -rn "<the number or phrase>" *.md docs audit index.html run_analysis.py`).
2. **Edit all surfaces in the same commit.** Never land "the doc now, the page
   later" — that is how the live site ends up builds behind the repo.
3. **Run the guards** (below), then push. If `index.html` changed, deploy.

## Clusters — when you change X, also update Y

### 1. Physics / headline numbers
Canonical: **`fermi_sim/`** (the engine). Everything else quotes it.

```
fermi_sim/*.py            <- the change is made HERE first
  web/physics.js          mirror port (then: node audit/calcs/audit_webjs.mjs)
  run_analysis.py         the printed report
  index.html              KPIs, methodology prose, tables
  docs/REPORT.md          tender report
  README.md               headline results section
  audit/AUDIT_COMPARISON.md   engine column of the cross-source tables
```
Guard: `audit/calcs/run_audits.py` (includes `audit_docs.py`, which pins many
cross-file numbers). **When you add a new cross-file number, add a guard for it
in `audit_docs.py`** — stale counts and retracted values are exactly what it
catches.

### 2. The auditor guide (the four-surface cluster)
Canonical: **`audit/EXTERNAL_AUDIT_SCOPE.md`** (full file-by-file scope).

```
audit/EXTERNAL_AUDIT_SCOPE.md      <- canonical: scope, tiers, claims, disclosures
  audit/README.md                  "Guide for an independent auditor" section
                                   AND the directory-map line
  index.html                       the on-page "Guide for an independent auditor
                                   (human or AI)" section (short version + link)
  audit/AUDIT_PROMPTS.md           the AI prompt set the guide points to
```
The guide addresses **human and AI reviewers identically** — same files, same
claims, same independence bar. Do not fork it into per-audience variants.

### 3. Audit results / counts
Canonical: the **suite output itself** (`run_audits.py` prints the live total).

```
audit/calcs/*                      <- the suite
  README.md                        "Run it" section check counts
  index.html                       methodology + repository sections
  audit/README.md                  summary table
  audit/AUDIT_COMPARISON.md        totals quoted in prose
```
Do **not** pin the exact live total in `audit_docs.py` (circular, churns every
added check) — only forbid *stale* counts there.

### 4. Attribution / PSI framing
Canonical: **`audit/AUDIT_COMPARISON.md` §4b** (provenance & priority record).

```
audit/AUDIT_COMPARISON.md §4b      <- full record lives here only
  index.html                       credit callout + References entry (short)
  docs/REPORT.md                   one-line attributions
  audit/psi/README.md              archive note
```
Style rule: shipped surfaces state what things ARE — no changelog framing
("previously...", "now supersedes..."), no self-flagellation. History belongs in
AUDIT_COMPARISON §4b and git.

### 5. Plans / issues
`docs/plans/NN-slug.md` + the GitHub issue (see `CLAUDE-issue.md`). Plans are
dated snapshots — do **not** retro-edit them to match later reality.

## Page anchors (index.html)

Methodology heading ids are **auto-slugged from the heading text** (script near
the bottom of `index.html`). Renaming a heading therefore **changes its URL**.
If a heading's anchor has ever been published, pin the old id explicitly
(`<h4 id="old-slug">New title</h4>` — the slug script respects an existing id)
and leave a comment saying why.

## What needs a deploy vs a docs-only push

| Changed | Action |
|---|---|
| `index.html`, `web/*.js` | commit → `tools/deploy.py` → commit+push BOTH Pages clones → push branch + main → poll live |
| only `.md` / `.py` (non-shipped) | commit → push branch + main. No deploy. |

A committed-but-not-deployed page change leaves the live site stale — this has
happened; the poll (`tmp/ro/poll_live.py`) is the check that it hasn't.

## Guards to run before pushing doc changes

```bash
.venv/bin/python audit/calcs/audit_docs.py     # cross-file numeric/claim consistency
.venv/bin/python tmp/ro/check_links.py         # repo link targets exist
node tmp/ro/syntax_check.mjs                   # only if index.html changed
```

Historical logs (dated audit runs, plan files) are records — never rewritten to
match the present.
