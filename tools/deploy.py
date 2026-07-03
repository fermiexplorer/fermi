#!/usr/bin/env python3
"""Deploy a verified, version-pinned build of index.html into the GitHub Pages clones.

Single source of truth for build identity — both values are DERIVED, never hand-typed:

  • BUILD = (highest existing b<N>.html across the clones) + 1.  You cannot forget to bump it and
            it is always monotonic.  (The old hand-edited BUILD froze the badge at "build 75" for
            three deploys because the deploy step replaced SRC_COMMIT but never BUILD.)
  • SHA   = `git rev-parse HEAD` of the source repo, with a clean-tree guard, so the badge always
            links to the exact committed source that was shipped.

The source index.html carries BUILD=0 / "build 0" as DEV sentinels; this script injects the real
`const BUILD = N` constant AND the no-JS `>build N</a>` fallback, inlines web/physics.js, replaces
SRC_COMMIT, then READS THE WRITTEN FILES BACK AND RE-VERIFIES every invariant. Any mismatch aborts
loudly — a stale or wrong build label (or a non-inlined / HEAD-pinned artifact) can no longer ship.

Usage:
  python3 tools/deploy.py              # derive identity, write + verify both clones
  python3 tools/deploy.py --dry-run    # build + verify the artifact in memory, write nothing

After it runs: commit & push each clone, then push the source branch.
"""
import os, re, sys, shutil, subprocess

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLONES = ["/home/adi/src/tmp/fermi-pages-2", "/home/adi/src/tmp/fermi-root"]
TAG = '<script src="web/physics.js"></script>'
TAG_STARS = '<script src="web/stars.js"></script>'             # inlined too — a cached stale stars.js once hid the crossing table
COPY = ["web/physics.js", "web/stars.js", "web/three.min.js", "favicon.svg"]  # kept fresh for older non-inlined builds
SHIPPED = ["index.html", "web/physics.js", "web/stars.js"]     # must be committed before we pin a SHA


def die(msg):
    sys.exit(f"ABORT: {msg}")


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def derive_sha():
    dirty = sh("git", "-C", SRC, "status", "--porcelain", *SHIPPED)
    if dirty:
        die("shipped files have uncommitted changes — commit them first so the build SHA matches "
            f"what ships:\n{dirty}")
    return sh("git", "-C", SRC, "rev-parse", "HEAD")


def next_build():
    mx = 0
    for c in CLONES:
        if not os.path.isdir(c):
            die(f"clone not found: {c}")
        for x in os.listdir(c):
            m = re.fullmatch(r"b(\d+)\.html", x)
            if m:
                mx = max(mx, int(m.group(1)))
    if mx == 0:
        die("no existing b<N>.html found in any clone — refusing to guess the first build number")
    return mx + 1


def build_artifact(build, sha):
    with open(os.path.join(SRC, "index.html"), encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(SRC, "web", "physics.js"), encoding="utf-8") as f:
        physjs = f.read()
    with open(os.path.join(SRC, "web", "stars.js"), encoding="utf-8") as f:
        starsjs = f.read()
    # every marker we rewrite must appear EXACTLY once, or our regex would silently mis-edit
    for marker in (TAG, TAG_STARS, "SRC_COMMIT = 'HEAD'"):
        if html.count(marker) != 1:
            die(f"marker {marker!r} found {html.count(marker)}x in source (expected 1)")
    for pat in (r"const BUILD = \d+", r">build \d+</a>"):
        n = len(re.findall(pat, html))
        if n != 1:
            die(f"pattern /{pat}/ found {n}x in source (expected 1)")
    art = html.replace(TAG, "<script>\n" + physjs + "\n</script>")          # self-contained
    art = art.replace(TAG_STARS, "<script>\n" + starsjs + "\n</script>")
    art = art.replace("SRC_COMMIT = 'HEAD'", f"SRC_COMMIT = '{sha}'")
    art = re.sub(r"const BUILD = \d+", f"const BUILD = {build}", art)
    art = re.sub(r">build \d+</a>", f">build {build}</a>", art)
    if len(art) <= len(html):
        die("physics.js inlining did not enlarge the artifact — inline failed")
    return art


def verify(text, build, sha, label):
    problems = []
    if not re.search(rf"const BUILD = {build}\b", text):
        problems.append(f"const BUILD is not {build}")
    if f">build {build}</a>" not in text:
        problems.append(f"no-JS fallback is not >build {build}</a>")
    if sha not in text:
        problems.append("source SHA not embedded")
    if "SRC_COMMIT = 'HEAD'" in text:
        problems.append("SRC_COMMIT still pinned to HEAD")
    if TAG in text:
        problems.append("physics.js still external (not inlined)")
    if TAG_STARS in text:
        problems.append("stars.js still external (not inlined) — stale-cache risk")
    if re.search(r">build 0</a>", text) or re.search(r"const BUILD = 0\b", text):
        problems.append("dev sentinel build 0 leaked into the artifact")
    if problems:
        die(f"[{label}] " + "; ".join(problems))


def main():
    dry = "--dry-run" in sys.argv
    sha = derive_sha()
    build = next_build()
    art = build_artifact(build, sha)
    verify(art, build, sha, "artifact")
    print(f"build {build}  sha {sha[:10]}  artifact {len(art):,} bytes  — verified in memory")
    if dry:
        print("--dry-run: nothing written")
        return
    for clone in CLONES:
        idx = os.path.join(clone, "index.html")
        bfile = os.path.join(clone, f"b{build}.html")
        if os.path.exists(bfile):
            die(f"{bfile} already exists — build-number collision")
        for path in (idx, bfile):
            with open(path, "w", encoding="utf-8") as f:
                f.write(art)
        os.makedirs(os.path.join(clone, "web"), exist_ok=True)
        for rel in COPY:
            shutil.copyfile(os.path.join(SRC, rel), os.path.join(clone, rel))
        # round-trip: re-read what we actually wrote and re-verify (catches a bad write/encoding)
        with open(idx, encoding="utf-8") as f:
            wrote_idx = f.read()
        with open(bfile, encoding="utf-8") as f:
            wrote_b = f.read()
        verify(wrote_idx, build, sha, f"{clone}/index.html")
        if wrote_idx != wrote_b:
            die(f"{clone}: index.html != b{build}.html after write")
        print(f"  {clone}: index.html + b{build}.html written + re-verified")
    print(f"done — build {build} deployed to {len(CLONES)} clones.")
    print("next: commit & push each clone, then push the source branch.")


if __name__ == "__main__":
    main()
