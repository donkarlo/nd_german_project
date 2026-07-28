#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 configure.py
exec python3 dictionary_app.py "$@"
