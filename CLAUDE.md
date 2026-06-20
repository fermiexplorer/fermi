# Fermi — Claude Code Instructions

## Communication Rules

- **Do not jump the gun.** When the user is asking questions or thinking out
  loud, ANSWER the questions. Do NOT start making code changes, deleting files,
  or refactoring until the user explicitly asks you to implement something.
- If unsure whether the user wants a change or is just exploring options, ASK.
- A question is not a request. "Why do we need X?" does not mean "delete X."
- Wait for a clear instruction like "go", "do it", "implement this", or similar
  before making changes.
- **Plan rejection means back to planning.** If the user rejects a plan or
  says "hang on" / "wait" / "not yet", stay in plan mode. Do NOT start
  implementing a revised approach without explicit plan approval. Update
  the plan, present it again, get approval, then code.
- **When in doubt, enter plan mode.** If unsure whether a change is trivial
  or needs discussion, enter plan mode. The cost of over-planning is low;
  the cost of implementing the wrong thing is high.
- **Fix by making consistent, not by removing.** When something looks wrong,
  fix it by making it match the rest of the system — not by removing it or
  adding a special case. Understand the design intent first.
- **Diagnose before fixing.** When a bug is reported, do a deep root cause
  analysis before proposing code changes. Explain the architecture, trace
  the failure path, explain WHY the design allowed this failure. Only then
  propose fixes.
- **Do not read files from other projects** (e.g., other repos under
  `~/src/`) unless the user explicitly tells you to. Stay within the
  current working directory.

## Critical Design Rules

- **`fermi_sim/` is the source of truth.** The Python engine is authoritative; the web
  calculator (`web/physics.js`) is a port of it. Any physics change must be made in
  `fermi_sim/` first, then mirrored to `web/physics.js`, and the parity audit
  (`node audits/audit_webjs.mjs`) must still pass.
- **Audits must stay independent.** Checks in `audits/` verify the math by a
  *different* method (astropy, conservation laws, brute-force optimisation, numerical
  integration) — never by calling the engine and comparing it to itself. Keep it that way.
- **No identifying third-party names in shipped artifacts** (web page, public docs).
  The mission is referred to only as "Fermi".
- **Don't silently change embedded constants.** The Alpha Centauri state vector in
  `web/physics.js` is copied from `fermi_sim`; if `fermi_sim/astro.py` changes, re-dump and
  re-run the parity audit.

## Project Overview

Fermi is a first-order ("Fermi estimate") simulation and interactive calculator for an
**interstellar precursor mission to Alpha Centauri**: deliver a ~1 kg payload to within
2600 AU of AC (99% of the way) inside 100,000 years, from LEO, on ion propulsion. It
sizes the vehicle, finds the minimum departure Δv and optimal arrival time, and compares
power architectures (solar vs fuel cell) and trajectories (direct vs gravity assist).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install numpy scipy astropy pytest
```

Node (any recent version) is used only for the web-parity audit.

## Running Tests

```bash
.venv/bin/pytest                      # smoke / regression tests
.venv/bin/python audits/run_audits.py # full independent audit suite (32 checks)
node audits/audit_webjs.mjs           # web JS <-> Python parity
.venv/bin/python audits/ui_playwright.py  # render the page in Chromium + screenshot
.venv/bin/python run_analysis.py      # print the integrated analysis
```

## Project Structure

- `fermi_sim/` — Python engine: `astro` (AC ephemeris), `intercept` (aim geometry),
  `departure` (LEO→v∞ Δv), `spacecraft` (mass/power), `trajectory` (cruise + assists).
- `run_analysis.py` — integrated analysis report (stdout).
- `index.html` + `web/physics.js` — interactive calculator (sliders/charts/methodology).
- `audits/` — independent verification suite (Python + a Node parity check).
- `docs/` — `REPORT.md` (tender feasibility report), `CODEX_AUDIT_PROMPTS.md`.
- `tests/` — pytest smoke tests. `tmp/ro/` — throwaway check scripts.

## Key Conventions

- **Language**: Python 3 (engine), vanilla JS (web). Follow PEP 8.
- **SI units everywhere** in the engine; convert to km/s, AU, yr only at display time.
- Physics functions are pure and dependency-light (numpy/scipy); plotting/UI is isolated.

## Push / Default Branch

Default branch is `main`. Branch before committing if on `main`.

## Banned Bash Patterns — NEVER USE

These trigger security prompts that block the console. Every violation wastes
user time. Use the listed alternative instead.

### Compound commands — NEVER combine in one Bash call

| Banned | Why | Use instead |
|--------|-----|-------------|
| `cd dir && git ...` | "bare repository attack" prompt | `git -C <path> ...` |
| `cd dir && gh ...` | same | `gh -R owner/repo ...` |
| `cmd1 && cmd2` | metachar prompt | separate Bash calls |
| `cmd1 ; cmd2` | metachar prompt | separate Bash calls |
| `cmd1 \|\| cmd2` | metachar prompt | separate Bash calls |
| `cd dir` + newline + `cmd` | compound command | `git -C` or separate calls |

### Shell operators — NEVER use in Bash

| Banned | Why | Use instead |
|--------|-----|-------------|
| `$(...)` | "shell operators" prompt | Write tool + `git commit -F tmp/commit-msg.txt` |
| heredocs (`<<`, `<<'EOF'`) | "shell operators" prompt | Write tool to create file, then run it |
| `>`, `<`, `>>` redirects | "output redirection" prompt | Write tool to create files |
| `2>&1` | redirect, not pipe — triggers prompt even before `\|` | drop entirely (stderr flows to terminal) |
| `\;`, `\|` backslash-escapes | "backslash before operator" prompt | temp script in `tmp/` |
| `python -c "..."` | metachar prompts on quotes | Write to `tmp/*.py`, then `python3 tmp/script.py` |
| `python3 << 'EOF'` | heredoc prompt | same |
| `--flag ""` before another `--flag` | "empty quotes before dash" false positive | restructure arguments |

### Tool misuse — use dedicated tools

| Banned | Why | Use instead |
|--------|-----|-------------|
| `grep`/`rg` as primary command | metachar prompts on `&`, `\|`, `(` in patterns | Grep tool |
| `find` | same | Glob tool |
| `cat`/`head`/`tail` | same | Read tool |
| `git show ... \| grep` | piped git output triggers prompts | Grep tool, or `git show <ref>:<path>` (no pipe) |

### Destructive commands — NEVER use without explicit user request

| Banned | Why |
|--------|-----|
| `rm`, `rm -rf` | file deletion |
| `git rm` | tracked file deletion |
| `git reset --hard` | discards uncommitted work |
| `git clean -f` | deletes untracked files |
| `git push --force` / `-f` | overwrites remote history |
| `git stash drop` | discards stashed work |

### Path rules

- **Bash**: relative paths only. NEVER `/home/...` or any absolute path.
- **Read/Write/Edit tools**: absolute paths are OK (these tools require them).
- **git**: always `git -C <relative-path>` — never `cd` + `git`.

### Multi-pipe chains — NEVER use inline

| Banned | Why | Use instead |
|--------|-----|-------------|
| `ps aux \| grep X \| grep -v grep \| awk ...` | multi-pipe triggers prompt | Write to `tmp/*.sh` or `tmp/*.py`, run the script |
| `kill $(pgrep ...)` | subshell + pipe | Write a `tmp/kill_proc.sh` script |
| Any chain with `\| awk`, `\| sed`, `\| cut` | triggers prompt | tmp script |

For process management (find PID, kill, restart), ALWAYS write a tmp script.

### What IS allowed

- Single commands with simple arguments
- ONE output pipe for filtering: `cmd | head`, `cmd | tail`, `cmd | grep`, `cmd | wc`
- `git -C path <subcommand>`

### WSL-specific bans

| Banned | Why | Use instead |
|--------|-----|-------------|
| `set -e` in scripts | invalid option on WSL bash | omit or use `set -o errexit` |
| backslash line continuations | breaks on WSL/CRLF | single-line commands or `--body-file` |

### Script Directories

| Directory | Purpose | Auto-approved |
|-----------|---------|---------------|
| `tmp/ro/` | Read-only checks, diagnostics | Yes |
| `tmp/rw/` | State-changing scripts | Selectively |
| `tmp/danger/` | Destructive operations | Never |

Write new scripts to the appropriate directory. Legacy `tmp/*.py` scripts
prompt for approval individually.

## Screenshots

**SS = See Screenshot.** When user says "SS", find the most recent `.png`
file across both screenshot directories and read it:

```python
# Check both locations, read the newest file
import glob, os
candidates = glob.glob("/tmp/screenshots/ss-*.png") + glob.glob("/mnt/c/Users/adi_o/Downloads/screenshots/ss-*.png")
latest = max(candidates, key=os.path.getmtime) if candidates else None
```

- **Local**: `/mnt/c/Users/adi_o/Downloads/screenshots/ss-local-{timestamp}.png`
- **Remote**: `/tmp/screenshots/ss-tower-{timestamp}.png`
- Each screenshot has a unique timestamped filename (never overwrites).

## Plans

All plans MUST be saved in `docs/plans/` as `NN-slug.md`. Every plan must include:
- **Push/merge instructions**: explicit steps for how the changes get committed,
  pushed, and (if applicable) merged via PR. Never leave changes uncommitted.
- **Verification steps**: how to confirm the plan was executed correctly.

## Issue Workflow

Every issue or work item should have an associated `docs/plans/NN-slug.md` file.
File the GitHub issue first to obtain the number, then create the plan file.
See `CLAUDE-issue.md` for the detailed process and plan file template.

Conventions for issue tracking:
- **Title prefix**: `NN — Title` (zero-padded issue number, em dash). Example: `05 — Fix widget`
- **Body plan link**: clickable markdown link, not backtick text.
  Use `[NN-slug.md](https://github.com/fermiexplorer/fermi/blob/main/docs/plans/NN-slug.md)`
- **Matrix summary tables**: `#` column uses `[#N](https://github.com/fermiexplorer/fermi/issues/N)` format

### Resolving issues

<!-- Optional: use this loop if/when Fermi adopts a convergence matrix. -->

Source of truth: `docs/plans/00-matrix.md`

1. **Read** — Open the issue and its plan file
2. **Plan** — Identify affected files
3. **Investigate** — Real bug, false positive, or needs-clarification?
4. **Fix** — Make the code change
5. **Test** — Run test suite
6. **Update matrix** — Mark resolved
7. **Commit** — One commit per issue

## Permissions

- Run read-only commands without asking for confirmation. This includes
  tests, check scripts, service restarts, and any state examination commands.
  NEVER block the console waiting for approval on read-only operations.
- No destructive git commands — `rm`, `git rm`, `git reset --hard`, `git clean`,
  `git push --force` must never be used without explicit user request.
- Prefer editing existing files over creating new ones.
- Git commit messages via file: Write tool → `tmp/commit-msg.txt`, then `git commit -F tmp/commit-msg.txt`.
- PR bodies via file: Write tool → `tmp/pr-body.txt`, then `gh pr create --body-file tmp/pr-body.txt`.
- File issues for discovered problems — don't ad-hoc fix tangents.
- Always file follow-up issues for residual work.

## Subagents

Every subagent prompt MUST include: "Use Grep/Glob/Read tools, not
grep/find/cat. No heredocs, redirects, `$(...)`, compound commands.
Use `git -C`. ONE command per Bash call. Relative paths only in Bash."

## Memory

Do **not** use Claude Code's auto-memory (`~/.claude/projects/.../memory/`).
That directory is NOT in git — anything stored there is invisible to code
review and cannot be tracked. ALL durable knowledge goes in repo files:
- Behavioral rules and conventions → `CLAUDE.md`
- Project context and data notes → `docs/`
- Engineering plans → `docs/plans/`
- Work tracking → GitHub Issues

NEVER write to `~/.claude/` for anything. If it's worth remembering, it's
worth committing to the repo.
