# GMAT outputs (published for inspection)

These are the **raw GMAT report files** and the **engine-vs-GMAT comparison**, committed so
the inputs (`../scripts/*.script`), the comparison script (`../compare.py`) and the actual
results are all inspectable in the repo without installing or running anything.
`../run_gmat.sh` regenerates them.

| File | What it is |
|------|------------|
| `01_impulsive.txt` | GMAT report for check 1 (impulsive departure). Pre- and post-burn `ElapsedSecs`, `Earth.RMAG`, `Earth.C3Energy`. The post-burn C3 = 379.8154 km²/s² = the engine's required v∞,Earth². |
| `02_lowthrust.txt` | GMAT report for check 2 (low-thrust escape spiral). Cartesian state (`X,Y,Z,VX,VY,VZ`), `RMAG` and `TotalMass` logged every 20000 s through the ~692-revolution spiral. `compare.py` finds the specific-energy (½v²−μ/r) = 0 crossing → escape time. |
| `comparison_result.txt` | Output of `compare.py`: the side-by-side engine-vs-GMAT numbers and PASS/FAIL. |

Generated with GMAT R2020a (Ubuntu x64, `GmatConsole`). See `../README.md` for the method.
