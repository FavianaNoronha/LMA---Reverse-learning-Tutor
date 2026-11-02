#!/usr/bin/env bash
# One command for the whole Gemma run. From the repo folder, with the venv active:
#   bash scripts/run_gemma_all.sh                 # gemma3:12b, quick profile (about 30-60 min)
#   bash scripts/run_gemma_all.sh gemma3:4b       # smaller model (8 GB Macs)
#   bash scripts/run_gemma_all.sh gemma3:12b full # the full profile (a few hours)
#   MOCK=1 bash scripts/run_gemma_all.sh          # offline dry run of the whole pipeline (NOT a result)
# Results go to docs/results_gemma/ and are zipped to docs/results_gemma/gemma_results.zip : send that zip back.
set -u
MODEL="${1:-gemma3:12b}"; PROFILE="${2:-quick}"; MOCK="${MOCK:-0}"
URL="${SETU_URL:-http://localhost:11434/v1}"
cd "$(dirname "$0")/.." || exit 1
OUT=docs/results_gemma; mkdir -p "$OUT"
case "$PROFILE" in full) LEAK_N=10; REPS=3; SIM_N=5; EVAL_N=10;; *) PROFILE=quick; LEAK_N=3; REPS=1; SIM_N=2; EVAL_N=3;; esac
START=$(date +%s); STARTED=$(date '+%Y-%m-%d %H:%M'); STEPS="$OUT/.steps"; : > "$STEPS"
if [ "$MOCK" = "1" ]; then MODEL_ARGS="--mock"; SIM_ARGS=""; MODEL="mock"; else MODEL_ARGS="--base-url $URL --model $MODEL"; SIM_ARGS="--base-url $URL --model $MODEL"; fi

step() { name="$1"; shift; echo; echo "=== $name"; "$@"; code=$?; echo "$name $code" >> "$STEPS"; return $code; }

if [ "$MOCK" != "1" ]; then
  python scripts/gemma_preflight.py --base-url "$URL" --model "$MODEL" --profile "$PROFILE" || { echo; echo "Stopped: fix the message above, then run this again."; exit 1; }
fi
step tests            python -m pytest -q
step leak_plain       python scripts/plain_prompt_leak_test.py $MODEL_ARGS --n $LEAK_N --out "$OUT/leak_plain.json"
if [ "$MOCK" != "1" ]; then cp "$OUT/leak_plain.json" docs/results_gemma_leak.json; fi     # the scorecard reads this path
step baselines        python scripts/gemma_baselines.py $MODEL_ARGS --reps $REPS --out "$OUT/baselines.json"
step controllability  python scripts/simulated_eval.py $SIM_ARGS --learners $EVAL_N --out "$OUT/simulated_eval.json"
step students         python scripts/simulate_students.py $SIM_ARGS --n $SIM_N --free --out "$OUT/students_llm.json"
step sim_learners     python scripts/simulate_learners.py $SIM_ARGS --n $SIM_N --default-only --out "$OUT/sim_learners.json"

END=$(date +%s)
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
MACHINE="$(uname -s) $(uname -m)"; if [ "$(uname -s)" = "Darwin" ]; then MACHINE="$(sysctl -n machdep.cpu.brand_string 2>/dev/null), $(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 )) GB RAM"; fi
python - "$OUT" "$MODEL" "$PROFILE" "$STARTED" "$(( (END-START)/60 ))" "$COMMIT" "$MACHINE" "$STEPS" <<'PY'
import json, sys
out, model, profile, started, minutes, commit, machine, steps = sys.argv[1:9]
st = {l.split()[0]: int(l.split()[1]) for l in open(steps) if l.strip()}
json.dump({"model": model, "profile": profile, "started": started, "minutes": int(minutes), "commit": commit, "machine": machine, "steps": st},
          open(f"{out}/run_info.json", "w"), indent=1)
PY
rm -f "$STEPS"
python scripts/gemma_summary.py > /dev/null
python scripts/evaluate.py > /dev/null 2>&1
( cd "$OUT" && rm -f gemma_results.zip && zip -q gemma_results.zip *.json SUMMARY.md )
echo; echo "DONE in $(( (END-START)/60 )) min. Send me this file:  $OUT/gemma_results.zip"
echo "(or just paste $OUT/SUMMARY.md)"
