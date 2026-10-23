#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found."
    exit 1
fi

source .venv/bin/activate

echo "=== ChronoSentinel AI ==="
echo "Project: $(pwd)"
echo ""

python -m py_compile app/dashboard.py app/cyber_dna.py scripts/classify_flows.py
echo "Python syntax checks passed."

echo ""
echo "Starting Streamlit dashboard..."
exec streamlit run app/dashboard.py
