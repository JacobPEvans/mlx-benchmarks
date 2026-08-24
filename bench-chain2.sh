#!/usr/bin/env bash
# Round 2: reasoning smokes only, using the arc_challenge_chat_qwen3 overlay.
set -uo pipefail
cd "$(dirname "$0")"
export MLX_EVAL_CONCURRENT=1
LOG="$PWD/bench-chain.log"
OUT="$PWD/run-output"

reasoning() { # $1=model $2=slug
  mlx-eval \
    --include_path configs/lm-eval/qwen3-tasks \
    --model local-chat-completions \
    --model_args "base_url=http://127.0.0.1:11434/v1/chat/completions,model=$1,num_concurrent=1,max_length=32768,timeout=3600" \
    --tasks arc_challenge_chat_qwen3 --limit 15 \
    --apply_chat_template --fewshot_as_multiturn --log_samples \
    --output_path "$OUT/$2/reasoning-smoke-r2" >>"$LOG" 2>&1
}

echo "=== [$(date '+%H:%M:%S')] ROUND 2 START (qwen3 overlay)" >>"$LOG"
reasoning "mlx-community/Qwen3-4B-Instruct-2507-4bit" qwen3-4b-instruct-2507 &&
  echo "=== r2 judge reasoning OK" >>"$LOG" || echo "=== r2 judge reasoning FAILED" >>"$LOG"
sleep 5
reasoning "mlx-community/Qwen3.5-9B-MLX-4bit" qwen35-9b &&
  echo "=== r2 small reasoning OK" >>"$LOG" || echo "=== r2 small reasoning FAILED" >>"$LOG"
echo "=== [$(date '+%H:%M:%S')] ROUND 2 COMPLETE" >>"$LOG"
