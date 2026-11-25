#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec unshare --user --map-root-user --net sh -ec '
    ip link set dev lo up
    exec python3 -B demo.py "$@"
' sh "$@"
