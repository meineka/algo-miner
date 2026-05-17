#!/usr/bin/env bash
# Build a single ZIP snapshot of the Aziz brain for ChatGPT review.
# Output: collab/<UTC_TIMESTAMP>_claude_export.zip
#
# Contents:
#   brain/        Python implementation of the Aziz rules + helpers
#   simulator/    Bar-by-bar backtester
#   mt5/          MetaTrader 5 Expert Advisor source + README + AUDIT
#   tests/        pytest suite
#   research/aziz/ Knowledge base + transcripts + video index
#   main.py + requirements.txt + CLAUDE.md
#   EXPORT_INFO.txt  manifest with git SHA, branch, file count

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

TS=$(date -u +%Y-%m-%dT%H-%MZ)
OUT_DIR="$ROOT/collab"
ZIP_PATH="$OUT_DIR/${TS}_claude_export.zip"
INFO_PATH="$OUT_DIR/${TS}_claude_export.info.md"

mkdir -p "$OUT_DIR"

# Manifest first so it lands inside the zip too
{
   echo "# Claude export — ${TS}"
   echo
   echo "- git branch : $(git rev-parse --abbrev-ref HEAD)"
   echo "- git SHA    : $(git rev-parse HEAD)"
   echo "- created at : ${TS} UTC"
   echo
   echo "## Last 10 commits"
   git log --oneline -10 | sed 's/^/    /'
   echo
   echo "## Contents"
   echo "- brain/         Python Aziz strategy engine (10 files)"
   echo "- simulator/     OHLC + trade simulator"
   echo "- mt5/           MetaTrader 5 Expert Advisor (Aziz_NQ.mq5)"
   echo "- tests/         pytest suite"
   echo "- research/aziz/ Living knowledge base + transcripts + video index"
   echo "- main.py, requirements.txt, CLAUDE.md"
   echo
   echo "## How to review"
   echo "1. Unzip locally"
   echo "2. Read research/aziz/knowledge.md (latest dated section at bottom is most recent finding)"
   echo "3. Read mt5/AUDIT.md for the EA's current state and open items"
   echo "4. To send feedback: write collab/${TS}_chatgpt_answer.md and commit+push"
} > "$INFO_PATH"

zip -r -q "$ZIP_PATH" \
   brain simulator mt5 tests research/aziz main.py requirements.txt CLAUDE.md \
   -x '*/__pycache__/*' '*.pyc'

# Also include the manifest inside the zip
( cd "$OUT_DIR" && zip -q "$(basename "$ZIP_PATH")" "$(basename "$INFO_PATH")" )

# Print summary
echo "Export ready:"
ls -lh "$ZIP_PATH" "$INFO_PATH" | sed 's/^/  /'
