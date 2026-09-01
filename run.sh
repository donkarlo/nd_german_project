#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

python3 src/nd_german/configure.py
exec python3 src/nd_german/app.py "$@"
