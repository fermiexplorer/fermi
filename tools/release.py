#!/usr/bin/env python3
"""One-command release — the ONLY way changes ship (scripts-only policy, CLAUDE.md).

    .venv/bin/python tools/release.py --msg-file tmp/commit-msg.txt --stage <paths...>

Steps (fail-fast, each echoed):
  1. git add <paths>; git commit -F <msg-file>
  2. If the commit touches a SHIPPED file (index.html / web/physics.js / web/stars.js):
     run tools/deploy.py, then commit + push BOTH Pages clones with the derived
     build number and source SHA.
  3. Push the source branch and HEAD:main.
  4. If deployed: poll the live site until the build badge flips (exit 2 on timeout
     so a re-poll can be run without redoing the release).

Run tools/verify.py (and ram_sweep.sh after any --ui run) BEFORE releasing.
"""
import argparse
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
PY = os.path.join(".venv", "bin", "python")
CLONES = [os.path.join("..", "tmp", "fermi-pages-2"), os.path.join("..", "tmp", "fermi-root")]
SHIPPED = {"index.html", "web/physics.js", "web/stars.js"}
LIVE_URL = "https://fermiexplorer.github.io/"


def run(cmd, timeout=120):
    print("+ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        sys.exit(f"RELEASE FAILED at: {' '.join(cmd)}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--msg-file", required=True)
    ap.add_argument("--stage", nargs="+", required=True)
    args = ap.parse_args()

    run(["git", "add", *args.stage])
    run(["git", "commit", "-F", args.msg_file])
    sha = run(["git", "rev-parse", "--short", "HEAD"]).strip()
    changed = run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"]).split()
    build = None

    if any(p in SHIPPED for p in changed):
        out = run([PY, "tools/deploy.py"], timeout=300)
        m = re.search(r"build (\d+)", out)
        if not m:
            sys.exit("RELEASE FAILED: could not parse build number from deploy.py output")
        build = m.group(1)
        with open(args.msg_file, encoding="utf-8") as fh:
            title = fh.readline().strip()[:70]
        for cl in CLONES:
            run(["git", "-C", cl, "add", "index.html", "web/physics.js", "web/stars.js",
                 f"b{build}.html"])
            run(["git", "-C", cl, "commit", "-m", f"build {build}: {title} (source {sha})"])
            run(["git", "-C", cl, "push", "origin", "main"], timeout=180)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
    run(["git", "push", "origin", branch], timeout=180)
    run(["git", "push", "origin", "HEAD:main"], timeout=180)

    if build:
        for i in range(24):                      # up to ~4 min
            try:
                with urllib.request.urlopen(LIVE_URL, timeout=15) as r:
                    html = r.read().decode("utf-8", "replace")
                if f">build {build}<" in html:
                    print(f"LIVE: build {build} confirmed")
                    break
            except OSError as e:
                print(f"  poll {i+1}: {e}")
            time.sleep(10)
        else:
            print(f"WARNING: live badge did not flip to build {build} within the poll window")
            sys.exit(2)

    print(f"RELEASE OK: {sha}" + (f" (build {build} live)" if build else " (docs-only, no deploy)"))


if __name__ == "__main__":
    main()
