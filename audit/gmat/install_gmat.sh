#!/usr/bin/env bash
#
# Install GMAT R2020a for the Fermi independent cross-validation.
#
# R2020a is the last NASA GMAT release that ships a Linux binary; newer releases
# (R2026a) are Windows/macOS only. This installer fetches the Ubuntu x64 build,
# which also runs under WSL. For Windows/macOS, see the notes printed below.
#
# Usage:   ./install_gmat.sh
# Result:  GMAT under  audit/gmat/.gmat-R2020a/GMAT/R2020a/   (git-ignored)
#          GmatConsole at  .../bin/GmatConsole
#
set -o errexit
set -o nounset

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GMAT_DIR="${GMAT_HOME:-$HERE/.gmat-R2020a}"
CACHE="$HERE/.cache"
TARBALL="gmat-ubuntu-x64-R2020a.tar.gz"
URL="https://downloads.sourceforge.net/project/gmat/GMAT/GMAT-R2020a/$TARBALL"

OS="$(uname -s)"
if [ "$OS" != "Linux" ]; then
  cat <<EOF
This installer downloads the GMAT R2020a *Linux* build (also works under WSL).
Detected OS: $OS

GMAT ships native binaries for your platform -- install one of these instead:
  Windows:  https://sourceforge.net/projects/gmat/files/GMAT/GMAT-R2026a/gmat-win-R2026a.zip
  macOS:    https://sourceforge.net/projects/gmat/files/GMAT/GMAT-R2026a/gmat-mac-x64-R2026a-signed.dmg

Then either:
  * GUI:     open each scripts/*.script in GMAT and Run, or
  * console: set GMAT_BIN to the dir containing GmatConsole(.exe) and run run_gmat.sh
Finally run:  python3 compare.py
EOF
  exit 0
fi

mkdir -p "$CACHE" "$GMAT_DIR"
if [ ! -f "$CACHE/$TARBALL" ]; then
  echo ">>> Downloading GMAT R2020a (~338 MB) ..."
  curl -L --retry 3 -o "$CACHE/$TARBALL" "$URL"
fi

echo ">>> Extracting ..."
tar -xzf "$CACHE/$TARBALL" -C "$GMAT_DIR"

BIN="$(dirname "$(find "$GMAT_DIR" -name GmatConsole -type f | head -1)")"
if [ -z "$BIN" ]; then
  echo "ERROR: GmatConsole not found after extraction." >&2
  exit 1
fi
echo
echo ">>> GMAT installed."
echo "    GmatConsole: $BIN/GmatConsole"
echo "    Next:        ./run_gmat.sh"
