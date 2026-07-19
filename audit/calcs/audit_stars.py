"""Audit 10 -- web/stars.js data invariants.

The regenerated encounter tables (builds 120-135) drive the page's star sections. A regen
bug (a min-solar-alpha below the escape floor, a stray non-null above the ~26.5 km/s
sizing ceiling, a propellant fraction inconsistent with its dv budget) would ship silently.
This guards the shipped JSON arrays directly by re-deriving their invariants.
"""

from __future__ import annotations

import json
import math
import os
import re

from _util import check

from fermi_sim import constants as c

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ESCAPE_FLOOR_WKG = 43.0     # bisected solar-escape edge at the page sizing (build 131)
CEILING_KMS = 26.5          # impulsive-from-1-AU limit of the fixed 20 km/s sizing budget
ISP = 3000.0


def _load(varname, src):
    m = re.search(varname + r"\s*=\s*(\[.*?\]);", src, re.S)
    return json.loads(m.group(1)) if m else None


def run() -> None:
    print("== Audit 10: star-data invariants (web/stars.js) ==")
    with open(os.path.join(ROOT, "web", "stars.js"), encoding="utf-8") as f:
        src = f.read()

    rows = []
    for v in ("ECLIPTIC_CROSSINGS_20LY", "CLOSEST_PASSES_100", "LUMINOUS_APPROACHERS"):
        r = _load(v, src)
        check(f"{v} parses ({len(r) if r else 0} rows)", bool(r))
        if r:
            rows += [(v, x) for x in r]

    ve = ISP * c.G0
    n_amin_below = n_amin_above = n_pf = 0
    for v, x in rows:
        amin = x.get("amin")
        cruise = x.get("vcr", x.get("vmin"))
        # (1) no amin below the solar-escape floor
        if amin is not None and amin < ESCAPE_FLOOR_WKG - 0.5:
            n_amin_below += 1
        # (2) no finite amin above the ~26.5 km/s sizing ceiling
        if amin is not None and cruise is not None and cruise > CEILING_KMS + 0.05:
            n_amin_above += 1
        # (3) propellant fraction consistent with the dv budget at Isp 3000
        dvb, pf = x.get("dvb"), x.get("pf")
        if dvb is not None and pf is not None:
            expect = 100.0 * (1.0 - math.exp(-dvb * 1e3 / ve))
            if abs(expect - pf) > 1.5:
                n_pf += 1

    check("no min-solar-alpha below the ~43 W/kg escape floor", n_amin_below == 0,
          f"{n_amin_below} rows")
    check(f"no finite alpha above the {CEILING_KMS} km/s sizing ceiling", n_amin_above == 0,
          f"{n_amin_above} rows")
    check("propellant % matches dv budget at Isp 3000 (all rows)", n_pf == 0, f"{n_pf} rows off")

    # (4) approachers actually approach (dpass <= dnow)
    lum = _load("LUMINOUS_APPROACHERS", src) or []
    bad = [r["n"] for r in lum if r.get("dpass") is not None and r.get("dnow") is not None
           and r["dpass"] > r["dnow"] + 0.1]
    check("luminous approachers close in (dpass <= dnow)", not bad, str(bad[:3]))

    # (5) boundary sanity: the largest cruise carrying a finite amin is <= the ceiling.
    max_amin_cruise = max((x.get("vcr", x.get("vmin")) for v, x in rows
                           if x.get("amin") is not None
                           and x.get("vcr", x.get("vmin")) is not None), default=0.0)
    check("max cruise with a finite alpha sits under the ceiling",
          max_amin_cruise <= CEILING_KMS + 0.05, f"{max_amin_cruise:.1f} km/s")


if __name__ == "__main__":
    from _util import summary
    run()
    raise SystemExit(summary())
