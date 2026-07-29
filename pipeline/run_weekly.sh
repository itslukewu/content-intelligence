#!/usr/bin/env bash
# Weekly Market Insight pipeline — 手动跑: ./run_weekly.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
WEEK=$(date +%G-W%V)
OUT_DIR="${VAULT_DIR:-$HOME/obsidian-vault}/market-insight"
mkdir -p "$OUT_DIR"

# ── Stage 1: 采集(替换成你的 viral_research_agent 实际命令)──
# python3 ~/viral_research_agent/run.py --out "$DIR/creator_intelligence.json"
[ -f "$DIR/creator_intelligence.json" ] || { echo "FAIL: no creator_intelligence.json (stage 1 未接入)"; exit 1; }

# ── Stage 2: 确定性分析(脚本算数)──
python3 "$DIR/audience-analyze.py" "$DIR/creator_intelligence.json" "$DIR/analysis.json"

# ── Stage 3: Founder 侧输入(过去 7 天笔记;缺失则降级而非中断)──
NOTES="$DIR/founder_notes.md"
if [ -d "${VAULT_DIR:-}" ]; then
  find "$VAULT_DIR" -name '*.md' -mtime -7 -not -path '*market-insight*' \
    -exec sh -c 'echo "## {}"; cat "{}"' \; > "$NOTES" 2>/dev/null || true
fi
[ -s "$NOTES" ] || echo "(founder notes unavailable this week — intersection degraded)" > "$NOTES"

# ── Stage 4: LLM 合成(Claude Code headless;数字禁改,只解释)──
claude -p "$(cat "$DIR/synthesize_prompt.md")

=== analysis.json ===
$(cat "$DIR/analysis.json")

=== founder_notes.md ===
$(cat "$NOTES")" > "$OUT_DIR/$WEEK-market-insight.md"

echo "OK: $OUT_DIR/$WEEK-market-insight.md"
