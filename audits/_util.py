"""Shared helpers for the audit suite.

Audits are *independent* cross-checks: they re-derive results with a different
method (astropy, brute-force optimisation, conservation laws, numerical
integration) and compare against the ``fermi_sim`` engine and the values published
in the web calculator. A circular check (call the engine, compare to itself) is
explicitly avoided.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> bool:
    _RESULTS.append((name, bool(passed), detail))
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail else ""))
    return bool(passed)


def close(a: float, b: float, rel: float = 1e-6, abs_: float = 0.0) -> bool:
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), abs_)


def rel_err(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-30)
    return abs(a - b) / denom


def summary() -> int:
    npass = sum(1 for _, p, _ in _RESULTS if p)
    ntot = len(_RESULTS)
    print(f"\n{'-' * 60}\nAUDIT SUMMARY: {npass}/{ntot} checks passed")
    failed = [n for n, p, _ in _RESULTS if not p]
    if failed:
        print("FAILED:")
        for n in failed:
            print(f"  - {n}")
        return 1
    print("ALL CHECKS PASSED")
    return 0
