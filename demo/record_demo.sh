#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# RAGTrace demo recorder
# Records the UI walkthrough and produces demo/demo.gif
#
# Usage:
#   ./demo/record_demo.sh              # auto mode (headless GIF)
#   ./demo/record_demo.sh --regen-data # also regenerate sample data first
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$REPO/demo"
PYTHON="${PYTHON:-python3}"

# ── Prefer the project venv if it has playwright installed ───
for candidate in \
    /Users/sabyasachighosh/Projects/rag_trace/.venv/bin/python \
    "$REPO/venv/bin/python" \
    "$REPO/.venv/bin/python"
do
    if "$candidate" -c "import playwright" 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

echo "Using Python: $PYTHON"

# ─── 1. Optionally regenerate sample data ────────────────────
if [[ "${1:-}" == "--regen-data" ]]; then
    echo "→ Regenerating sample data…"
    cd "$REPO"
    "$PYTHON" ui/generate_test_data_v2.py
fi

# ─── 2. Ensure API server is running ─────────────────────────
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sessions | grep -q "200"; then
    echo "→ Starting API server on :8000…"
    cd "$REPO"
    nohup "$PYTHON" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 \
        > /tmp/ragtrace_api.log 2>&1 &
    API_PID=$!
    echo "  API PID: $API_PID"
    sleep 3
    if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/sessions | grep -q "200"; then
        echo "✗ API server failed to start. Check /tmp/ragtrace_api.log"
        exit 1
    fi
    echo "  ✓ API ready"
else
    echo "→ API already running on :8000"
fi

# ─── 3. Ensure UI server is running ──────────────────────────
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    echo "→ Starting UI server on :3000…"
    cd "$REPO"
    nohup "$PYTHON" ui/serve.py > /tmp/ragtrace_ui.log 2>&1 &
    UI_PID=$!
    echo "  UI PID: $UI_PID"
    sleep 2
    if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
        echo "✗ UI server failed to start. Check /tmp/ragtrace_ui.log"
        exit 1
    fi
    echo "  ✓ UI ready"
else
    echo "→ UI already running on :3000"
fi

# ─── 4. Install playwright/Pillow if missing ─────────────────
"$PYTHON" -c "import playwright, PIL" 2>/dev/null || {
    echo "→ Installing playwright and Pillow…"
    "$PYTHON" -m pip install --quiet playwright Pillow
    "$PYTHON" -m playwright install chromium
}

# ─── 5. Generate the GIF ─────────────────────────────────────
echo "→ Recording demo…"
cd "$REPO"
"$PYTHON" "$DEMO/make_demo_gif.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Demo GIF saved to: $DEMO/demo.gif"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
open "$DEMO/demo.gif" 2>/dev/null || true
