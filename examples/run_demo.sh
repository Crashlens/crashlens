#!/usr/bin/env bash
set -euo pipefail
echo "Running CrashLens demo scan using examples/demo-logs.jsonl"
crashlens scan --demo || true
echo "Demo run complete. Check report.md or report_format_json.json"
