#!/usr/bin/env bash
# WSL RAM hygiene (this box has ~8 GB; Cursor already holds ~1.5 GB, and it has
# OOM-crashed from accumulated tooling). Kills ONLY the orphaned helper processes
# THIS project spawns — Playwright browsers, screenshot/test http.servers, and GMAT
# console runs. It does NOT touch Cursor / Electron / system processes, and it does
# NOT delete any disk cache (the GMAT install etc. stay put).
#
# Run it after any Playwright/GMAT run that was interrupted or timed out, or whenever
# RAM feels tight:   bash tools/ram_sweep.sh

sweep() {   # $1 = pgrep -f regex, $2 = human label
  local pids
  pids=$(pgrep -f "$1" || true)
  if [ -n "$pids" ]; then
    echo "  $2: killing $(echo "$pids" | tr '\n' ' ')"
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(pgrep -f "$1" || true)
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  else
    echo "  $2: none"
  fi
}

echo "RAM sweep — orphaned project tools only (no disk touched):"
sweep 'ms-playwright'   'Playwright browsers'
sweep 'http\.server'    'screenshot/test http.server'
sweep 'GmatConsole'     'GMAT console'
echo "--"
free -h | awk 'NR<=2'
