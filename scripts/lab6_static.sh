#!/usr/bin/env bash
# Analiza statyczna SUT (zajęcia nr 6 / blok P4).
# Używa narzędzi z .venv (albo .tools_bin). Instalacja:
#   uv sync --group dev
#   # albo: uv pip install radon pylint flake8
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TARGET="${1:-API.py}"

if [[ -x "$ROOT/.venv/bin/radon" ]]; then
  BIN="$ROOT/.venv/bin"
elif [[ -x "$ROOT/.tools_bin/radon" ]]; then
  BIN="$ROOT/.tools_bin"
  export PYTHONPATH="$ROOT/.tools_vendor${PYTHONPATH:+:$PYTHONPATH}"
else
  echo "Brak radon w .venv. Zainstaluj:" >&2
  echo "  uv sync --group dev" >&2
  echo "  # albo: uv pip install radon pylint flake8" >&2
  exit 1
fi

RADON="$BIN/radon"
FLAKE8="$BIN/flake8"
PYLINT="$BIN/pylint"

echo "=== radon cc (złożoność cyklomatyczna) ==="
"$RADON" cc "$TARGET" -s -a

echo
echo "=== radon mi (indeks utrzymywalności) ==="
"$RADON" mi "$TARGET" -s

echo
echo "=== radon raw ==="
"$RADON" raw "$TARGET" -s

echo
echo "=== flake8 ==="
"$FLAKE8" "$TARGET" || true

echo
echo "=== pylint ==="
export PYLINTHOME="${PYLINTHOME:-$ROOT/.pylint_cache}"
mkdir -p "$PYLINTHOME"
"$PYLINT" "$TARGET" --score=y || true
