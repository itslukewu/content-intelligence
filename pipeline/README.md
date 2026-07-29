# Weekly Market Insight Pipeline

五段流水线,只有 Stage 4 用 LLM:

    Stage 1  viral_research_agent(Apify 采集)→ creator_intelligence.json
    Stage 2  audience-analyze.py(确定性:聚类/供需/frames/emerging/health)→ analysis.json
    Stage 3  Obsidian 近 7 天笔记 → founder_notes.md(入场券素材)
    Stage 4  claude -p + 冻结 prompt(只解释,不算数)→ 报告
    Stage 5  写入 vault/market-insight/YYYY-Wnn-market-insight.md

## 安装
1. 三个文件放同一目录:audience-analyze.py / synthesize_prompt.md / run_weekly.sh
2. 在 run_weekly.sh Stage 1 处接入你的 viral_research_agent 命令
3. export VAULT_DIR=~/你的/obsidian/vault

## 每周调度(周一 07:00)
macOS(launchd,推荐,睡眠唤醒后会补跑):
  ~/Library/LaunchAgents/com.luke.market-insight.plist →
    ProgramArguments: /path/to/run_weekly.sh
    StartCalendarInterval: {Weekday: 1, Hour: 7, Minute: 0}
  launchctl load ~/Library/LaunchAgents/com.luke.market-insight.plist

Linux(cron):
  0 7 * * 1 VAULT_DIR=$HOME/vault /path/to/run_weekly.sh >> ~/market-insight.log 2>&1

## 失败策略(fail-soft)
- Stage 1 失败 → 整条中断并报错(没有新数据就不该有新报告)
- Stage 3 缺笔记 → 继续跑,报告 Intersection 段标 degraded
- health.warnings 永远出现在报告开头:先看 Health,再看结论

## 每周唯一的人工动作
读报告 → 从 Top 5 里挑 1-2 条实际去写 → 这个"采用/不采用"就是系统的反馈信号
