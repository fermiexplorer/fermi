#!/usr/bin/env bash
#
# Run the GMAT cross-validation scripts headless and compare against fermi_sim.
#
# Locates GmatConsole (from GMAT_BIN, GMAT_HOME, or the local install_gmat.sh dir),
# points GMAT's OUTPUT_PATH at this folder so the scripts' relative out/*.txt land
# here, runs both .script files, restores the startup file, then runs compare.py.
#
# Usage:   ./run_gmat.sh
#
set -o errexit
set -o nounset

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- locate GmatConsole ----
BIN=""
if [ -n "${GMAT_BIN:-}" ]; then
  BIN="$GMAT_BIN"
elif [ -n "${GMAT_HOME:-}" ]; then
  BIN="$(dirname "$(find "$GMAT_HOME" -name GmatConsole -type f 2>/dev/null | head -1)")"
else
  BIN="$(dirname "$(find "$HERE/.gmat-R2020a" -name GmatConsole -type f 2>/dev/null | head -1)")"
fi
if [ -z "$BIN" ] || [ ! -x "$BIN/GmatConsole" ]; then
  echo "GmatConsole not found. Run ./install_gmat.sh first, or set GMAT_BIN." >&2
  exit 1
fi
echo ">>> Using GmatConsole: $BIN/GmatConsole"

mkdir -p "$HERE/out"

# ---- point GMAT OUTPUT_PATH at this folder (so out/*.txt resolves here) ----
STARTUP="$BIN/gmat_startup_file.txt"
cp "$STARTUP" "$STARTUP.fermi-bak"
trap 'mv -f "$STARTUP.fermi-bak" "$STARTUP" 2>/dev/null || true' EXIT
sed -i "s|^OUTPUT_PATH .*|OUTPUT_PATH              = $HERE/|" "$STARTUP"

run_one() {
  echo ">>> GMAT running $1 ..."
  LD_LIBRARY_PATH="$BIN" "$BIN/GmatConsole" "$HERE/scripts/$1" | tail -3
}
run_one 01_impulsive_departure.script
run_one 02_lowthrust_escape.script

# ---- compare against fermi_sim (prefer the project venv) ----
PY="python3"
if [ -x "$HERE/../../.venv/bin/python" ]; then PY="$HERE/../../.venv/bin/python"; fi
echo
"$PY" "$HERE/compare.py"
