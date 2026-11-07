#!/usr/bin/env bash
# Prompt ablation: remove one reliability/policy rule at a time from the system prompt and measure
# which failure comes back. Needs ANTHROPIC_API_KEY. Records one cassette per variant.
#   ANTHROPIC_API_KEY=... scripts/ablation.sh [model] [runs-per-scenario] [chaos]
# Cost: about 50 runs x ~6 model calls per variant. Replay any variant offline afterwards:
#   agentproof compare --agents replay:cassettes/ablation/no-retry.jsonl@no-retry --runs 6 --chaos 0.3
set -euo pipefail
cd "$(dirname "$0")/.."
export MODEL="${1:-claude-sonnet-5-5}" RUNS="${2:-6}" CHAOS="${3:-0.3}" PYTHONPATH=src
mkdir -p cassettes/ablation reports/ablation
run() {
  v="$1"; spec="claude:$MODEL"; [ "$v" = "full" ] || spec="$spec@$v"
  AGENTPROOF_CASSETTE="cassettes/ablation/$v.jsonl" python3 -m agentproof compare \
    --agents "$spec" --runs "$RUNS" --chaos "$CHAOS" --out "reports/ablation/$v" > "reports/ablation/$v.txt" 2>&1 || true
}
export -f run
printf '%s\n' full no-idempotency no-untrusted-notes no-retry no-already-refunded no-limit bare | xargs -P 4 -I{} bash -c 'run {}'
echo "done"
