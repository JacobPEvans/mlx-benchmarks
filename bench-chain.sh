#!/usr/bin/env bash
# Sequential quick-eval chain: one actor per host, models run one at a time.
# Judge 4B first (free), then poll for the 9B slot to clear (pi-agent holds it).
set -uo pipefail

WT="/Users/jevans/git/public/ai/mlx-benchmarks/quick-evals-0823"
OUT="$WT/run-output"
LOG="$WT/bench-chain.log"
JUDGE="mlx-community/Qwen3-4B-Instruct-2507-4bit"
SMALL="mlx-community/Qwen3.5-9B-MLX-4bit"

export MLX_EVAL_CONCURRENT=1
export OPENAI_API_KEY=dummy
mkdir -p "$OUT"

step() { echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG"; }

reasoning() { # $1=model $2=slug
  mlx-eval \
    --include_path configs/lm-eval/qwen3-tasks \
    --model local-chat-completions \
    --model_args "base_url=http://127.0.0.1:11434/v1/chat/completions,model=$1,num_concurrent=1,max_length=32768,timeout=3600" \
    --tasks arc_challenge_chat_qwen3 --limit 15 \
    --apply_chat_template --fewshot_as_multiturn --log_samples \
    --output_path "$OUT/$2/reasoning-smoke" >>"$LOG" 2>&1
}

agentic() { # $1=model $2=slug
  (cd "$WT" && uv run harness/agentic/run.py \
    --base-url http://127.0.0.1:11434/v1 \
    --model "$1" \
    --cells conc1_think-on_ctx-small_stream \
    --repeats 5 \
    --output "$OUT/agentic_quick_$2.json") >>"$LOG" 2>&1
}

wait_9b_free() {
  local tries=10
  for i in "$(seq "$tries")"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 240 \
      http://127.0.0.1:11434/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -d "{\"model\":\"$SMALL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":4}")
    if [ "$code" = "200" ]; then step "9B slot free after probe $i"; return 0; fi
    step "9B still contended (HTTP $code), probe $i/$tries — sleeping 180s"
    sleep 180
  done
  step "WARN: 9B never freed; proceeding WITH CONTENTION CAVEAT"
  return 0
}

step "CHAIN START"
step "--- phase 1: judge 4B"
reasoning "$JUDGE" qwen3-4b-instruct-2507 && step "judge reasoning OK" || step "judge reasoning FAILED"
agentic  "$JUDGE" qwen3-4b-instruct-2507 && step "judge agentic OK"   || step "judge agentic FAILED"

step "--- phase 2: small 9B"
wait_9b_free
reasoning "$SMALL" qwen35-9b && step "small reasoning OK" || step "small reasoning FAILED"
agentic  "$SMALL" qwen35-9b && step "small agentic OK"    || step "small agentic FAILED"

step "CHAIN COMPLETE"
