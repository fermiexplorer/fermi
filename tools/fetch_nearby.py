"""Fetch 6-D kinematics for nearby stars from SIMBAD TAP (ADQL, JSON).

Step 1 of the star-table pipeline (see tools/make_starmap_data.py for the whole chain);
writes tmp/ro/nearby_stars.json (not committed — a re-fetchable SIMBAD dump).

Volume: parallax >= 20 mas (<= 50 pc = 163 ly) — wide enough that anything able to
reach the Sun's neighbourhood within ~1.5 Myr at stellar speeds (<~100 km/s) is included.
Requires RV + proper motion (full 6-D state needed to propagate).
"""
import json
import os
import urllib.parse
import urllib.request

os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))   # repo root

# Wide volume: plx >= 10 mas (<= 100 pc = 326 ly). A star farther out reaching the solar
# neighbourhood within ~1 Myr would need > ~150 km/s — beyond disk-star speeds.
ADQL = """
SELECT b.main_id, b.ra, b.dec, b.plx_value, b.pmra, b.pmdec,
       b.rvz_radvel, b.sp_type, f.V
FROM basic b LEFT JOIN allfluxes f ON b.oid = f.oidref
WHERE b.plx_value >= 10 AND b.rvz_radvel IS NOT NULL
  AND b.pmra IS NOT NULL AND b.pmdec IS NOT NULL
ORDER BY plx_value DESC
"""
# Supplement: the region's GIANTS — very bright stars out to ~1000 ly (plx >= 3), so a
# huge star inbound from beyond the main volume cannot be missed.
ADQL_GIANTS = """
SELECT b.main_id, b.ra, b.dec, b.plx_value, b.pmra, b.pmdec,
       b.rvz_radvel, b.sp_type, f.V
FROM basic b JOIN allfluxes f ON b.oid = f.oidref
WHERE b.plx_value >= 3 AND b.plx_value < 10 AND f.V <= 2.5
  AND b.rvz_radvel IS NOT NULL AND b.pmra IS NOT NULL AND b.pmdec IS NOT NULL
"""
def fetch(q, maxrec=120000):
    url = ("https://simbad.u-strasbg.fr/simbad/sim-tap/sync?" +
           urllib.parse.urlencode({"request": "doQuery", "lang": "adql",
                                   "format": "json", "query": q, "MAXREC": str(maxrec)}))
    req = urllib.request.Request(url, headers={"User-Agent": "fermi-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print("SERVER SAID:", e.read().decode("utf-8", "replace")[:2000])
        raise SystemExit(1)

data = fetch(ADQL)
giants = fetch(ADQL_GIANTS)
seen = {r[0] for r in data["data"]}
extra = [r for r in giants["data"] if r[0] not in seen]
data["data"] = data["data"] + extra
out = "tmp/ro/nearby_stars.json"
with open(out, "w") as fh:
    json.dump(data, fh)
print(f"fetched {len(seen)} stars (plx>=10) + {len(extra)} bright giants (plx 3-10, V<=2.5) -> {out}")
print("columns:", [m["name"] for m in data.get("metadata", [])])
