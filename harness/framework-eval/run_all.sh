#!/usr/bin/env bash
# Agent Framework Evaluation — run all 4 frameworks back-to-back.
#
# Each script declares its deps via PEP 723 inline metadata; `uv run --with`
# adds pinned minimums on top. No changes to pyproject.toml or uv.lock required.
#
# Usage: ./harness/framework-eval/run_all.sh
# Prereqs: vllm-mlx running at localhost:11434 with tool-call-parser enabled

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create test fixture
echo "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the English alphabet and is commonly used as a typing exercise." > /tmp/eval-test.txt

echo "============================================================"
echo "  Agent Framework Evaluation — $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Model: ${MLX_DEFAULT_MODEL:?MLX_DEFAULT_MODEL not set}"
echo "  Server: ${MLX_API_URL:-http://127.0.0.1:11434/v1}"
echo "============================================================"

echo ""
echo ">>> 1/4: OpenAI tool-calling (baseline — raw OpenAI client, no framework)"
uv run --with "openai>=1.0.0" "$SCRIPT_DIR/eval_openai_tool_calling.py" 2>&1

echo ""
echo ">>> 2/4: Qwen-Agent (official Qwen framework)"
uv run --with "qwen-agent>=0.0.14,soundfile>=0.13.0" "$SCRIPT_DIR/eval_qwen_agent.py" 2>&1

echo ""
echo ">>> 3/4: smolagents (HuggingFace)"
uv run --with "smolagents>=1.0.0" "$SCRIPT_DIR/eval_smolagents.py" 2>&1

echo ""
echo ">>> 4/4: Google ADK"
uv run --with "google-adk>=0.5.0" "$SCRIPT_DIR/eval_google_adk.py" 2>&1

echo ""
echo "============================================================"
echo "  Evaluation complete — $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
