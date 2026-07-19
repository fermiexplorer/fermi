"""Audit 9 -- cross-file documentation consistency.

Not a physics check: greps the shipped/authored artifacts (index.html, docs/REPORT.md,
README.md, run_analysis.py, CLAUDE.md) for the numeric claims and verdicts that builds
131-135 propagated, so drift between them is caught automatically. This is the guard the
"default switch outran the prose" class of miss (builds 131-135) needed.
"""

from __future__ import annotations

import os

from _util import check

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def run() -> None:
    print("== Audit 9: cross-file documentation consistency ==")

    idx = _read("index.html")
    report = _read("docs/REPORT.md")
    readme = _read("README.md")
    analysis = _read("run_analysis.py")
    claude = _read("CLAUDE.md")

    # 1. Audit-suite count references must carry no stale earlier counts (the exact live
    #    count is not pinned here — that would be circular and churn on every added check;
    #    _util.summary() is the authority on the live total).
    for stale in ("41 checks", "55 checks", "73 checks", "86 checks", "90 checks", "126 checks"):
        check(f"CLAUDE.md/index.html/README carry no stale '{stale}'",
              stale not in claude and stale not in idx and stale not in readme)
    check("README quotes 35 parity, no stale 20/71 JS/UI",
          "35 JS-parity" in readme and "20 JS-parity" not in readme and "71 checks" not in readme)

    # 2. The pumped two-leg total is 31-34 everywhere it appears (no stale 30-32).
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("README.md", readme),
                    ("run_analysis.py", analysis)):
        check(f"{nm} has no stale '~30-32' / '30–32' SEP total", "30-32" not in txt and "30–32" not in txt)

    # 3. The GTO Earth-leg is ~4.0, not the retracted ~4.2.
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("run_analysis.py", analysis)):
        check(f"{nm} GTO leg is ~4.0 (no stale ~4.2)", "4.2 km/s" not in txt or "4.24" in txt)

    # 4. The pumping threshold is stated as the non-monotone working-region EDGE (2.24e-4),
    #    never the retracted monotone "2.25e-4 failure threshold".
    for nm, txt in (("REPORT.md", report), ("run_analysis.py", analysis)):
        low = txt.lower()
        check(f"{nm} does not assert a monotone 2.25e-4 failure threshold",
              "2.25×10⁻⁴ failure threshold" not in txt and "2.25e-4 failure" not in low)

    # 5. Verdict coherence: REPORT must recommend pumped SEP and NOT still say pure solar
    #    "does not close" as its standing verdict, nor list "Three architectures do".
    check("REPORT recommends SEP + perihelion pumping",
          "SEP + perihelion pumping" in report and "recommended (default) architecture is **SEP" in report)
    check("REPORT no longer lists only 'Three architectures do'", "Three architectures do:" not in report)
    check("REPORT does not name nuclear-electric 'the recommended closing architecture'",
          "recommended closing architecture is **nuclear" not in report)
    check("REPORT section 3 is the constant-power fallback, not 'the pure-electric closure'",
          "## 3. The pure-electric closure" not in report)
    check("REPORT has exactly one architecture headed 'recommended (default)' and it is pumping",
          report.count("recommended (default)") == 1
          and "recommended (default) architecture is **SEP" in report)

    # 6. The alpha band for pumping is the corrected 15-21 (not the retracted 13-25).
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("run_analysis.py", analysis)):
        check(f"{nm} pumping alpha band is 15-21 (no stale 13-25)",
              "13-25 W/kg" not in txt and "13–25 W/kg" not in txt)

    # 7. run_analysis verdict leads with the pumped pure-solar closure.
    check("run_analysis verdict states pure solar closes via pumping",
          "PURE SOLAR-ELECTRIC CLOSES" in analysis and "perihelion" in analysis.lower())


if __name__ == "__main__":
    from _util import summary
    run()
    raise SystemExit(summary())
