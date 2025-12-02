#!/usr/bin/env bash
set -euo pipefail
TARGET=${1:-http://localhost:8000}
echo "Smoke test placeholder: hitting $TARGET (replace with real endpoint if using proxy mode)"
curl -s -X POST "$TARGET/v1/chat/completions" -H "Content-Type: application/json" -d '{"model":"gpt-4","messages":[{"role":"user","content":"repeat loop"}]}' -w "\nHTTP_CODE:%{http_code}\n" || true
