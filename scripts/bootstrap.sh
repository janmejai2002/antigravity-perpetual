#!/usr/bin/env bash
# Antigravity Perpetual - POSIX Bootstrap & Launch Script (Linux / macOS / WSL)
set -euo pipefail

echo "=========================================================================="
echo " [+] ANTIGRAVITY PERPETUAL BOOTSTRAP RUNNER (POSIX)"
echo "=========================================================================="

if ! command -v python3 &> /dev/null; then
    echo "[-] Python 3 is required but not found."
    exit 1
fi

echo " [+] Python Runtime: $(command -v python3)"

# Verify dependencies
if ! python3 -c "import fastapi, uvicorn, pydantic, yaml, psutil, requests" &> /dev/null; then
    echo " [*] Installing requirements.txt..."
    python3 -m pip install -r requirements.txt --quiet
fi

# Run tests
echo " [*] Running unit tests..."
python3 -m pytest --quiet || true

# Launch
echo "=========================================================================="
echo " [✓] Launching Perpetual Supervisor..."
echo "=========================================================================="
python3 -m antigravity_perpetual run
