#!/usr/bin/env bash

set -e

echo "======================================"
echo "Magma SDK (Unix)"
echo "======================================"

# =========================
# [1/4] Python detection
# =========================
echo "[1/4] Checking Python..."

PYTHON=""

if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python not found in PATH"
    exit 1
fi

echo "Using: $PYTHON"

# =========================
# [2/4] venv
# =========================
VENV_DIR=".venv"

echo "[2/4] Setting up venv..."

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    $PYTHON -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

PYTHON="$VENV_DIR/bin/python"

# =========================
# [3/4] dependencies (only once)
# =========================
echo "[3/4] Checking dependencies..."

REQ_FILE="requirements.txt"
REQ_MARKER="$VENV_DIR/requirements.installed"

if [ -f "$REQ_FILE" ]; then
    if [ ! -f "$REQ_MARKER" ]; then
        echo "Installing dependencies (first run only)..."
        $PYTHON -m pip install -r "$REQ_FILE"
        touch "$REQ_MARKER"
    else
        echo "Dependencies already installed"
    fi
else
    echo "No requirements.txt found, skipping"
fi

# =========================
# [4/4] run
# =========================
echo "[4/4] Running SDK..."
echo "--------------------------------------"

$PYTHON main.py "$@"