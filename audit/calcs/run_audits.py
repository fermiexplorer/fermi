"""Run the full independent audit suite.

Usage:  .venv/bin/python audit/calcs/run_audits.py
Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import _util
import audit_departure
import audit_ephemeris
import audit_fuelcell
import audit_intercept
import audit_propulsion
import audit_pumping
import audit_solar
import audit_synchrotron


def main() -> int:
    for mod in (
        audit_ephemeris,
        audit_intercept,
        audit_departure,
        audit_propulsion,
        audit_fuelcell,
        audit_solar,
        audit_pumping,
        audit_synchrotron,
    ):
        mod.run()
        print()
    return _util.summary()


if __name__ == "__main__":
    raise SystemExit(main())
