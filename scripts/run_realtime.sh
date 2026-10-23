#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "========================================"
echo " ChronoSentinel AI - Real-Time Monitor"
echo "========================================"

# 1. Start the existing local WAF services.
docker compose -f compose.yaml up -d

# 2. Confirm the supervised model exists.
if [[ ! -f models/chronosentinel_supervised.joblib ]]; then
  echo "ERROR: Supervised model not found."
  exit 1
fi

# 3. Check raw packet capture permission without capturing traffic.
python - <<'PY'
import socket
try:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                      socket.htons(3))
    s.close()
    print("Raw packet socket: AVAILABLE")
except Exception as exc:
    print(f"Raw packet socket: UNAVAILABLE ({exc})")
    print("WAF log monitoring will still be available.")
PY

# 4. Avoid launching a duplicate dashboard.
if curl -fsS --max-time 2 http://localhost:8501/ >/dev/null; then
  echo "Dashboard already responds at http://localhost:8501/"
else
  echo "Starting Streamlit dashboard..."
  streamlit run app/dashboard.py \
    --server.headless true \
    --server.port 8501 &
  DASH_PID=$!
  echo "Dashboard process: $DASH_PID"
fi

echo ""
echo "Dashboard: http://localhost:8501/"
echo "WAF endpoint: http://localhost:8080/"
echo ""
echo "Starting live WAF event collector."
echo "Keep this terminal open; press Ctrl+C to stop the collector."
echo "Open another terminal to browse the dashboard."
echo ""

exec python app/event_collector.py
