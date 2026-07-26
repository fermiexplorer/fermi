"""Fetch ALL published RV measurements for the plx>=20mas volume and build per-star
medians — robust against single-outlier catalog rows (the 2023MNRAS.519.5472M problem
that gave ksi Boo −21.3 vs a century of +2..+5, and c UMa −38.6 vs −14.5).

Step 2 of the star-table pipeline (see tools/make_starmap_data.py for the whole chain);
writes tmp/ro/rv_medians.json (not committed — a re-fetchable SIMBAD dump)."""
import json
import os
import statistics
import urllib.parse
import urllib.request

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))   # repo root

ADQL = """
SELECT b.main_id, v.velValue, v.bibcode, v.quality
FROM basic b JOIN mesVelocities v ON v.oidref = b.oid
WHERE b.plx_value >= 10 AND v.velValue IS NOT NULL
"""
url = ("https://simbad.u-strasbg.fr/simbad/sim-tap/sync?" +
       urllib.parse.urlencode({"request": "doQuery", "lang": "adql", "format": "json",
                               "query": ADQL, "MAXREC": "500000"}))
req = urllib.request.Request(url, headers={"User-Agent": "fermi-audit/1.0"})
with urllib.request.urlopen(req, timeout=300) as r:
    data = json.load(r)
rows = data["data"]
print(f"RV measurements fetched: {len(rows)}")
GAIA = ("2018yCat.1345....0G", "2022yCat.1355....0G")   # DR2 preferred, then DR3
per = {}
for name, v, bib, q in rows:
    per.setdefault(name, []).append((float(v), bib, (q or "").strip()))
best = {}
for n, vs in per.items():
    vals = [v for v, b, q in vs]
    med = statistics.median(vals)
    mad = statistics.median(abs(v - med) for v in vals)
    chosen = None
    for gb in GAIA:                                     # Gaia with quality A/B wins
        g = [v for v, b, q in vs if b == gb and q in ("A", "B")]
        if g:
            chosen = {"rv": g[0], "src": "gaia", "n": len(vs), "mad": round(mad, 2)}
            break
    if chosen is None:                                  # else median of ALL measurements
        chosen = {"rv": med, "src": "median", "n": len(vs), "mad": round(mad, 2)}
    best[n] = chosen
with open("tmp/ro/rv_medians.json", "w") as fh:
    json.dump(best, fh)
print(f"stars with measurements: {len(best)}")
for n in ("* ksi Boo", "* ksi Boo A", "* c UMa", "* lam Ser", "HD 168442",
          "LSPM J2146+3813", "HD   7924", "HD 204521", "* alf Cen"):
    if n in best:
        b = best[n]
        print(f"  {n}: {b['rv']:+.2f} km/s ({b['src']}, {b['n']} meas.)")
