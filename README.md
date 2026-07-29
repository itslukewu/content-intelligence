# content-intelligence

> AI-powered content intelligence pipeline: signal detection -> topic selection -> evidence ranking.

Part of the Founder OS ecosystem.

## What This Is

content-intelligence is an AI-powered pipeline for detecting signals, selecting topics, and ranking evidence for content creation. It supports Founder OS by turning raw market and audience inputs into structured publishing intelligence.

## Architecture

Placeholder.

## Design Principles

Placeholder.

## Status

In Progress

## Current Delivery

本次提交内容(2026-07-18 ~ 07-21 架构会话):

- `specs/` — 冻结规格与 Parked 提案(V2 冻结 + V2.1/V3 提案,含验收 ID P1-A1…)
- `prompts/` — 冻结 Prompt(周报合成 `synthesize_prompt`、选题 `intersection_prompt`)
- `pipeline/` — 每周自动化流水线(`run_weekly.sh` + `README`;活跃分析脚本为 `audience-analyze.py`)
- `reports/` — 第一份 Market Insight 报告(227 帖 / 12 创作者)

依赖链: V2 Phase 1(动工区) -> V2.1(Parked) -> V2 解冻 -> V3(Parked)
