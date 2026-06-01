#!/bin/sh
set -eu

ODA_REAL_PATH="${ODA_REAL_PATH:-/usr/bin/ODAFileConverter_27.1.0.0/ODAFileConverter}"
ODA_DIR="$(dirname "$ODA_REAL_PATH")"

export LD_LIBRARY_PATH="$ODA_DIR:$ODA_DIR/lib:${LD_LIBRARY_PATH:-}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-root}"

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

exec xvfb-run -a "$ODA_REAL_PATH" "$@"
