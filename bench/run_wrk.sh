#!/usr/bin/env bash
set -euo pipefail
TARGET=${1:-http://localhost:8000/v1/chat/completions}
OUT=bench/results.md
mkdir -p bench
echo "Running wrk benchmark against $TARGET" > $OUT
echo "Command: wrk -t2 -c100 -d10s --latency $TARGET" >> $OUT
wrk -t2 -c100 -d10s --latency "$TARGET" >> $OUT || true
echo "DONE" >> $OUT
