# Codex Conclusions v02

Deep re-review of the current `main` code and docs after the v01 conclusions were
merged. Review date: 2026-06-20.

## Bottom Line

The core propulsion feasibility conclusion still holds. The latest model remains
internally consistent: a roughly 500 kg wet solar-electric vehicle, about 20 km/s
realistic low-thrust design budget, about 248 kg xenon at Isp 3000 s, and a best
direct-departure window around 70,000-80,000 years.

The latest code improves the previous solar-array weakness. Instead of a fixed
150 W/kg assumption, it now computes physical array area and mass from solar flux,
cell efficiency, and areal density. The default commercial-silicon case is about
18.37 m^2 and 55.1 kg at 5 kW and 1 AU, leaving about 150 kg of the 255 kg dry mass
for bus, payload, and margin after array, engine/PPU, and tankage.

## Verification Run

- `.venv/bin/pytest`: 8/8 passed.
- `.venv/bin/python audits/run_audits.py`: 41/41 passed.
- `node audits/audit_webjs.mjs`: 10/10 passed.
- `.venv/bin/python run_analysis.py`: completed and reports the exact direct floor
  at 72,792 years.
- `.venv/bin/python audits/ui_playwright.py`: passed after rerunning outside the
  command sandbox; Chromium rendered all 7 charts, exercised tech dropdowns and
  Play, and reported no console errors.

## Confirmed Conclusions

1. Alpha Centauri state reconstruction remains sound. The Astropy cross-check still
   matches distance, velocity magnitude/direction, radial velocity, and closest
   approach.

2. The exact direct-departure floor remains 13.875 km/s at 72,792 years. The
   75,000-year benchmark is still practically equivalent at 13.886 km/s, only about
   10.3 m/s above the floor.

3. The low-thrust direct model remains bracketed, not fully optimized: about
   13.9 km/s impulsive floor, about 25.1 km/s naive continuous spiral, and about
   20 km/s as the engineering benchmark controlled by the web slider.

4. The fuel-cell conclusion is unchanged and stronger after the silicon-array
   update. At Isp 3000 s, H2/O2 fuel-cell reactant mass is about 37.3 tonnes, about
   677x the default 55.1 kg solar array. At the mass-optimal fuel-cell point, total
   consumables are still about 28.3 tonnes.

5. The new solar subsystem model closes for the baseline: 55.1 kg array, 30 kg
   engine/PPU, 19.9 kg tankage, and 150.0 kg bus/payload/margin remainder inside
   255 kg dry mass.

6. The web physics port remains aligned with Python for intercept, departure,
   rocket equation, and solar-array area checks.

7. The UI currently renders successfully under Playwright when Chromium is allowed
   to run outside the command sandbox.

## New Findings

1. README verification and headline numbers are stale. `README.md` still says the
   baseline uses a ~33 kg solar array and that the audit suite has 32 Python checks
   plus 8 JS checks. Current code and audits report a 55.1 kg silicon array, 41
   Python checks, and 10 JS parity checks.

2. `docs/REPORT.md` still says the burn uses a ~33 kg solar array. This conflicts
   with the current physical silicon-array model and `run_analysis.py`, which report
   about 55 kg at the default 5 kW, 20% efficiency, 3 kg/m^2 setting.

3. `index.html` still says the departure-delta-v optimum is "~75k yr" in the
   methodology text. The report and analysis now correctly state the exact floor
   near 72,800 years and explain why 75,000 years is an acceptable benchmark.

4. Shipped web content reintroduced identifying vendor/product names despite the
   repo rule against such names in shipped artifacts. Current examples include
   Starlink/SpaceX and ExoTerra in `index.html`, plus Starlink-class wording in
   `run_analysis.py` and `fermi_sim/spacecraft.py` comments/docstrings.

5. The references section in `index.html` relies heavily on Wikipedia and a vendor
   homepage for values presented as sources. For a tender-facing artifact, replace
   these with primary sources where possible: mission pages, datasheets, papers, or
   standards.

6. The browser propellant selector is partly cosmetic. Selecting Krypton or Argon
   changes tank fraction and labels, but does not model propellant-specific thruster
   performance, density, storage volume, cost, or available Isp/efficiency.

7. The browser badge still says "Xenon fraction" even after selecting Krypton or
   Argon. KPIs and mass chart labels use the selected propellant name correctly, so
   this is a localized UI text bug.

8. `index.html` says "No third-party site code was used" while the page loads Plotly
   from a CDN. The README correctly notes that the calculator needs internet for
   the Plotly CDN, so the web-page footer should be clarified.

9. The solar audit verifies the arithmetic and checks that 91 W/kg lands in a broad
   believable band. It still does not independently validate the default 20% cell
   efficiency, 3 kg/m^2 areal density, 6 kg/kW engine/PPU mass, or 8% tank fraction
   against primary data.

10. The UI Playwright audit is valuable but environment-sensitive. It failed inside
    the command sandbox because Chromium could not shut down its sandbox host, then
    passed outside the sandbox. This should be documented so future reviewers do not
    misread the first failure as an application failure.

## Recommended Next Fixes

1. Update README and report counts/numbers to match the current 41-check audit suite,
   10-check JS parity suite, and 55 kg default silicon array.

2. Remove or generalize shipped vendor/product names in `index.html` and public docs;
   keep primary source citations without brand-specific marketing labels unless
   there is a clear repo-approved reason.

3. Replace Wikipedia/vendor homepage references with primary sources and explicitly
   label unsourced defaults as assumptions.

4. Either make the propellant selector affect a documented physics parameter, or
   label it as a tankage/label sensitivity control only.

5. Add a small JS/UI assertion for the propellant badge text so the Krypton/Argon
   label path is covered.

6. Consider adding an explicit audit for the exact 72,792-year departure optimum,
   since the current suite verifies the broad 70,000-80,000 year region but not the
   exact minimized value printed by `run_analysis.py`.
