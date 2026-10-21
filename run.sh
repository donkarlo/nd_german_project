#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

if [[ -n "${ND_GERMAN_PYTHON:-}" ]]; then
    PYTHON="$ND_GERMAN_PYTHON"
else
    PYTHON=""
    for candidate in "$HOME/phd-venv/bin/python" "$HOME/myenv/bin/python" python3.13 python3.12 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import PySide6" >/dev/null 2>&1; then
            PYTHON="$candidate"
            break
        fi
    done
    if [[ -z "$PYTHON" ]]; then
        echo "PySide6 not installed in available Python environments." >&2
        exit 1
    fi
fi
"$PYTHON" src/nd_german/configure.py
exec "$PYTHON" src/nd_german/app.py "$@"
