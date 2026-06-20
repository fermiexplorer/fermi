# Issue Creation Process

Steps for filing a new issue and linking it to the convergence matrix.

## 1. File a GitHub issue

Write a brief summary to `tmp/issue-body.txt` (plan link added in step 3):

```bash
gh -R fermiexplorer/fermi issue create --title "Title" --body-file tmp/issue-body.txt
```

Note the issue number N returned by `gh`. Then prefix the title with the
zero-padded issue number:

```bash
gh -R fermiexplorer/fermi issue edit N --title "NN — Title"
```

Example: `gh issue edit 42 -R fermiexplorer/fermi --title "42 — New widget"`
(single-digit issues zero-pad: `05 — ...`).

## 2. Create the plan file

Create `docs/plans/NN-slug.md` where **NN is the GitHub issue number** (zero-padded
to two digits). For example, issue #7 → `07-slug.md`.

### Plan file template

```markdown
# NN — Title

GitHub issue: https://github.com/fermiexplorer/fermi/issues/N

## Problem

{What is wrong or missing. Reference spec sections/tables.}

## Affected Components

| Component | Status | Notes |
|-----------|--------|-------|
| {component} | {OK/BUG/MISS/PARTIAL/—} | |

## Fix

{What to change, in which file(s).}

## Tests

{Existing tests that cover this. New tests to add.}

## Acceptance Criteria

- [ ] Code change implemented
- [ ] Tests pass
- [ ] Matrix row updated
```

## 3. Update issue body with plan link

Rewrite `tmp/issue-body.txt` to include a clickable markdown link to the plan file:

```
[NN-slug.md](https://github.com/fermiexplorer/fermi/blob/main/docs/plans/NN-slug.md)

{One-line summary of the problem.}
```

Then update the issue:

```bash
gh -R fermiexplorer/fermi issue edit N --body-file tmp/issue-body.txt
```

## 4. Update the convergence matrix

Add a row to the appropriate section in `docs/plans/00-matrix.md` (or your
project's equivalent tracking file).

- **# column** (main tables) — the issue number (zero-padded): `07`
- **# column** (summary tables) — linked issue number:
  `[#N](https://github.com/fermiexplorer/fermi/issues/N)`
- **Item column** — link to the plan file:
  `[Title](https://github.com/fermiexplorer/fermi/blob/main/docs/plans/NN-slug.md)`
- **Issue column** — link to the GitHub issue:
  `[#N](https://github.com/fermiexplorer/fermi/issues/N)`

Fill in component status columns using the legend at the top of the matrix.

## 5. Commit

Stage the plan file and the matrix update together. Reference the issue number
in the commit message:

```
NN — Title (#N)
```
