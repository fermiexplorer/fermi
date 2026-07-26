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

## 4. Cross-link the issue and its plan

The GitHub issue is the tracker (there is no convergence-matrix file). Keep the
issue and its plan file cross-referenced:

- The **issue body** links its plan file:
  `[Title](https://github.com/fermiexplorer/fermi/blob/main/docs/plans/NN-slug.md)`
- The **plan file** references its issue number `#N` in its header.
- When related issues need a summary, link each by number:
  `[#N](https://github.com/fermiexplorer/fermi/issues/N)`.

## 5. Commit

Stage the plan file (and any code change) together. Reference the issue number
in the commit message:

```
NN — Title (#N)
```
