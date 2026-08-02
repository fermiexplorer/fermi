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
    for stale in ("41 checks", "55 checks", "73 checks", "86 checks",
                  "126 checks", "130 checks", "139 checks", "160 checks",
                  "172 checks", "187 checks", "82 checks", "84 checks", "88 checks"):
        check(f"CLAUDE.md/index.html/README carry no stale '{stale}'",
              stale not in claude and stale not in idx and stale not in readme)
    check("README parity count is current-generation, no stale 20/35/71 JS/UI",
          "46 JS-parity" in readme and "35 JS-parity" not in readme
          and "20 JS-parity" not in readme and "71 checks" not in readme)

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

    # 8. Ecliptic-crossing arrival year is ~79k everywhere (engine 79,252 yr); the retracted
    #    ~80,000-yr rounding must not reappear in REPORT's closing paragraph.
    check("REPORT states ecliptic crossing as ~79k, not ~80k",
          "80,000 yr at the ecliptic" not in report
          and ("79,000 yr at the ecliptic" in report or "79,250-yr" in report
               or "79,250 yr" in report))

    # 9. Synchrotron aperture-transit prose: the transit is ~0.5 s (t = Δv/a), NOT "milliseconds"
    #    (a build-141 error wrong by ~500×), and the coupling is gigawatt-class at probe scale, not
    #    "terawatt per transit". Pins the corrected copy so the physics claim can't silently drift back.
    check("index.html synchrotron transit is ~0.5 s, not milliseconds",
          "crossed in milliseconds" not in idx and "crossed in about half a second" in idx)
    check("index.html synchrotron coupling is gigawatt-class, not terawatt-per-transit",
          "terawatt-class coupling" not in idx and "terawatt-class pulse" not in idx
          and "gigawatt-class coupling" in idx)

    # 9b. The synchrotron is presented as an EXPLORATORY concept, not a candidate mission
    #     architecture (owner decision): the labeling must survive on the selector, the
    #     architecture table, the section header, and the analysis verdict.
    check("index.html labels the synchrotron exploratory in the architecture table",
          "Exploratory only — not a candidate for this mission" in idx)
    check("index.html synchrotron section opens with the exploratory status",
          "exploratory concept — not a candidate for this mission" in idx)
    check("run_analysis synchrotron verdict is labelled exploratory",
          "EXPLORATORY CONCEPT, NOT A CANDIDATE ARCHITECTURE" in analysis)

    # 9c. PP is THE mission architecture (owner decision, issue #12): the selector marks
    #     pumped as the mission and every alternative as exploratory, and each exploratory
    #     verdict states its blocking gate.
    check("index.html radio marks pumped as the mission architecture",
          "the mission architecture</b></label>" in idx)
    check("index.html radios mark all four alternatives exploratory",
          idx.count("— exploratory</label>") == 4)
    check("index.html architecture table states the direct gate (array does not exist)",
          "Exploratory — the array it needs does not exist" in idx)
    check("index.html architecture table states the Oberth gate (new engineering)",
          "Exploratory — new engineering, not catalog parts" in idx)
    check("index.html architecture table states the Jupiter gate (windows + ops)",
          "Exploratory — window-contingent, assist-class operations" in idx)
    check("index.html pumped verdict leads with THE MISSION ARCHITECTURE",
          "THE MISSION ARCHITECTURE — the only one that closes on parts you can order today"
          in idx)
    for nm, txt in (("REPORT.md", report), ("run_analysis.py", analysis)):
        check(f"{nm} frames one closing architecture + exploratory alternatives",
              "MISSION ARCHITECTURE" in txt and "xploratory" in txt)

    # 10. Thermal-era cross-file facts (issue #5). The derived cap 3.54 and the flown
    #     campaign dv 24.44 must appear on the headline surfaces; the old default budget
    #     bands must not reappear as the current default.
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("README.md", readme)):
        check(f"{nm} states the derived thermal cap 3.54",
              "3.54" in txt)
    for nm, txt in (("index.html", idx), ("REPORT.md", report)):
        check(f"{nm} states the flown thermal campaign dv 24.44",
              "24.44" in txt)
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("README.md", readme),
                    ("run_analysis.py", analysis)):
        check(f"{nm} carries no stale '31–34'/'31-34' default budget band",
              "31–34 km/s" not in txt and "31-34 km/s" not in txt)
    # 10b. Issue-#9 derived plane tax: the retired bolt-on pricing phrases must not
    #      resurface, and the new basin/budget facts must be stated on every headline
    #      surface (the crossing YEAR ~79,250 remains a geometric fact and stays).
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("README.md", readme),
                    ("run_analysis.py", analysis)):
        check(f"{nm} carries no stale '~1 km/s plane change' bolt-on pricing",
              "~1 km/s plane change" not in txt and "+ ~1 plane change" not in txt
              and "33.1 at the default aim" not in txt)
        check(f"{nm} states the pumped basin (~77.5-77.8k bottom, sub-noise)",
              "77,800" in txt or "77,500" in txt)
        check(f"{nm} states the ~32.3 km/s pumped two-leg total (at ITS own optimum)",
              "32.3" in txt and "32.6 km/s" not in txt)

    # the 4x-cap dv (23.14) may appear ONLY with an idealised/4x/PSI label nearby
    for nm, txt in (("index.html", idx), ("REPORT.md", report), ("README.md", readme)):
        ok = True
        pos = 0
        while True:
            i = txt.find("23.14", pos)
            if i < 0:
                break
            ctx = txt[max(0, i - 400):i + 400].lower()
            if not ("4×" in txt[max(0, i - 400):i + 400] or "4x" in ctx or "psi" in ctx
                    or "idealised" in ctx or "idealized" in ctx):
                ok = False
            pos = i + 1
        check(f"{nm} labels every 23.14 km/s mention as the idealised-4x/PSI-comparable figure", ok)

    # 11. PSI final assessment (July 2026): both archived PDFs must exist, and the page's
    #     PSI links must point at the FINAL report (the TR-numbered working draft stays
    #     archived but is no longer the cited surface).
    psi_final = "PSI_FermiExplorerInterstellarPrecursor_FeasibilityAssessment.pdf"
    for f in (psi_final, "PSI-TR-2026-0714.pdf", "crosscheck_final.py"):
        check(f"audit/psi/{f} is archived",
              os.path.exists(os.path.join(ROOT, "audit", "psi", f)))
    check("index.html cites the PSI final-assessment PDF", psi_final in idx)
    check("index.html no longer links the working-draft PDF as the citation",
          "PSI-TR-2026-0714.pdf" not in idx)


if __name__ == "__main__":
    from _util import summary
    run()
    raise SystemExit(summary())
