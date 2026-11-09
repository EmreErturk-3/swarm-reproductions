#!/usr/bin/env bash
#
# Builds ARGoS 3.0.0-beta59 and the Kilobot plugin (commit 381db2a) and installs
# both under $ARGOS_PREFIX (default ~/.local/opt/argos3), without root rights.
#
# System packages, installed once with root rights (Ubuntu 24.04):
#   sudo apt install build-essential cmake git pkg-config \
#     libfreeimage-dev libfreeimageplus-dev qtbase5-dev libqt5opengl5-dev \
#     freeglut3-dev libxi-dev libxmu-dev liblua5.3-dev lua5.3 python3-matplotlib
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${ARGOS_SRC:-$HOME/.local/src}"
ARGOS_TAG=3.0.0-beta59
KILOBOT_COMMIT=381db2af675b08ba847dc599ec7285b3340b652a

source "$SCRIPT_DIR/env.sh"
mkdir -p "$SRC"

if [ ! -d "$SRC/argos3" ]; then
  git clone --branch "$ARGOS_TAG" --depth 1 https://github.com/ilpincy/argos3.git "$SRC/argos3"
fi
if [ ! -d "$SRC/argos3-kilobot" ]; then
  git clone https://github.com/ilpincy/argos3-kilobot.git "$SRC/argos3-kilobot"
fi
git -C "$SRC/argos3-kilobot" checkout --quiet "$KILOBOT_COMMIT"

cmake -S "$SRC/argos3/src" -B "$SRC/argos3/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$ARGOS_PREFIX" \
  -DARGOS_DOCUMENTATION=OFF \
  -DARGOS_INSTALL_LDSOCONF=OFF
cmake --build "$SRC/argos3/build" --parallel
cmake --install "$SRC/argos3/build"

cmake -S "$SRC/argos3-kilobot/src" -B "$SRC/argos3-kilobot/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$ARGOS_PREFIX"
cmake --build "$SRC/argos3-kilobot/build" --parallel
cmake --install "$SRC/argos3-kilobot/build"

argos3 --version
