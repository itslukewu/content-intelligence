# Frontier Signal Agent — V3 提案

**日期**:2026-07-18(rev 3)
**状态**:**Parked — 不在当前 Scope 内,接口已稳定**
**性质**:对 V2 冻结区条目「Fast Signal 自动化(新闻抓取管道)」的解冻申请
**解锁条件**:V2 解冻条件达成(Phase 1–3 全部通过验收,且 Intersection 连续四周输出被实际采用的话题)。在此之前,本提案只读不建;Fast Signal 维持人工阅读 + Daily Review。
**rev 3 目标**:冻结全部接口(时间字段、confidence 规则、Health Block),使解锁后可直接实现,无需回头改规格。

本提案按 Architecture Rule 补齐输入 / 输出 / 验收三项。

---

## 定位

不是 News Agent。它收集的不是「今天发生了什么」,而是「什么会改变 AI-first Founder 的工作方式」。

**核心价值 = Lead Time**:Creator 层是滞后 7–14 天的传播回声(V2 数据已证实)。在 Creator 饱和传播之前完成 学习 → 实验 → 经历,配合 Evidence Gate,这个时间差即内容护城河。

**系统哲学**:竞争优势不来自更快消费信息,而来自更快把可靠信息转化为可验证的实践(Validated Experience)。本 Agent 因此是「学习与实践的优先级系统」的最上游,不是新闻聚合器。

**继承规则(不可修改)**:Frontier Signal 属于 Fast Signal,其输出**永不直接进入话题候选池**。合法去向仅两个:(a) Gap Detector 学习清单(learning);(b) 触发真实实验。

---

## 输入 — Source Tiers(冻结)

| Tier | 来源 | 抓取方式 | V3 阶段 |
|---|---|---|---|
| T1 官方 | OpenAI News、Anthropic Blog/Docs、Claude Docs、Cursor Changelog、Vercel Changelog、Cloudflare Blog、GitHub Changelog、MCP 规范 | RSS / 官方页面,稳定 | **V3.0** |
| T3 开发者 | GitHub Release / RFC / Issue(核心 repo 维护者) | GitHub API,稳定 | **V3.0** |
| T2 创始人 | Sam Altman、Dario Amodei、Karpathy、Rauch 等本人的 X / Blog / Newsletter | X 抓取,成本高且脆弱 | V3.1(推迟) |
| T4 Creator | 现有 Creator Intelligence | 已有 | 不属于本 Agent;仅作「传播确认层」引用 |

**分层理由**:T1 + T3-GitHub 有稳定 RSS/API,零反爬成本;T2 是全方案最贵最脆的一环,且信息损失小——重大发布在数小时内均有 T1/T3 对应物。T4 是传播层不是信号源,只用于事后验证 lead time。

---

## Signal Admission Rule(冻结)

进入 Decision Brief 的前置条件:**信号必须引用至少一个一手工件(first-hand artifact)**——

```text
可接受工件:Official Release / Changelog / 官方 Docs / 协议规范 /
           API 文档 / RFC / 已合并 PR / GitHub Release / 官方公告原文
不可接受:媒体转述、传闻、预测("OpenAI 可能…")、无链接的转发
```

**架构原则:数据源可以增加,证据标准不能降低。** 未来即使引入 Reddit / Hacker News / X / Discord 作为发现渠道,Admission Rule 不变——任何渠道发现的信号都必须回溯到一手工件才可入选。

- V3.0 下此规则自动满足(输入源只有 T1/T3),但仍须写入实现,作为对未来输入扩展的防线。
- V3.1 引入 T2 后:创始人帖子**单独不可入选**——须附一手工件链接方可正常入选;无工件的重要表态最多以 `confidence: low` + `action: watch` 记录。
- 不满足者在入口处直接丢弃(ignore 是准入门的输出,不是 Brief 内的 action),并计入 Health Block 的 rejected。

---

## 时间字段(冻结)

`first_seen` 语义易漂移,拆分为两个字段:

```yaml
published_at: <ISO 8601>   # 工件的官方发布时间(来自 RSS / API 元数据)
detected_at:  <ISO 8601>   # 本 Agent 首次发现该信号的时间
```

由此可精确定义两个此前混在一起的指标:

- **Detection Latency** = detected_at − published_at:管道健康指标,衡量 RSS/API 抓取延迟,进入 Health 监控。
- **Lead Time** = T4 Creator 传播起始时间 − detected_at:本 Agent 的核心 KPI,即 Luke 实际获得的先发窗口。验收时按此计算,不再使用含混的 first_seen。

---

## Confidence 规则(冻结)

confidence 由**工件类型确定性映射**,禁止 LLM 主观判断:

| confidence | 工件类型 |
|---|---|
| high | 已发布的 Release / Changelog / 正式 Docs / 已定稿协议规范 / 已合并 PR(已交付之物) |
| medium | 官方 Blog 公告 / 处于讨论中的 RFC / 未合并 PR(已宣布或进行中之物) |
| low | 创始人表态且无工件对应(V3.1 起;仅可 action: watch) |

**冻结理由**:confidence 若交给模型逐条判断,会随模型更换而漂移并逐渐失去区分度。映射表固定后,confidence 是数据属性,不是模型意见。

---

## 输出 — Daily Decision Brief

每日一个 Markdown 文件,**Frontmatter 结构冻结**(不建 Database,但格式保证未来可无重构直接 parse 入库):

```yaml
---
date: <YYYY-MM-DD>
signal_count: <int>          # 0 为合法值
health:
  signals_seen: <int>        # 抓取到的原始条目数
  admitted: <int>
  rejected: <int>            # 未过准入门(含无一手工件)
  duplicates_removed: <int>
  empty_output: <bool>
  tier_distribution: {T1: <int>, T2: <int>, T3: <int>}
  detection_latency_median_hours: <float>
  warnings: [<string>, ...]
signals:
  - signal: <一句话事实>
    signal_type: release | paper | api | pricing | policy | tool | protocol | benchmark
    source_tier: T1 | T2 | T3
    source_url: <一手工件链接,必填>
    published_at: <ISO 8601>
    detected_at: <ISO 8601>
    confidence: high | medium | low   # 按冻结映射表,非模型判断
    impact:                  # 锚定冻结的系统清单,禁止新增评审对象
      amazon_pipeline: 0-5
      content_intelligence: 0-5
      pkm: 0-5
      brand: 0-5
    time_horizon: today | week | month | quarter
    why: <一句话:这改变了你当前实际在跑的哪个工作流>
    action: watch | learn | experiment
---
```

每日 ≤ 5 条。字段规则:

- **signal_type**:冻结枚举,保证未来可直接统计「协议变化 vs 模型变化」等分布,无需重新分类。
- **action**:冻结枚举,仅三值 `watch | learn | experiment`。`ignore` 不是 Brief 内的 action——被准入门丢弃的信号不进入 Brief;一条既被收录又标 ignore 的信号视为准入门失效。
- **time_horizon**:重要性与时效性分离。Impact 回答「重要吗」,time_horizon 回答「什么时候重要」。Bug 修复可能 impact 全 0 / today;MCP 类协议变化可能 quarter / ★★★★★。排序时二者独立参与。
- **source_url 必填**:由 Admission Rule 保证。

**阅读纪律(与 Creator Intelligence 一致)**:先看 Health,再看 Signal。

**Impact 评审问题(冻结)**:「这是否改变 Luke 当前实际运行的某个工作流?」——禁止参考新闻热度、传播量、媒体覆盖。

**空输出合法(冻结)**:`signal_count: 0` 是正确且预期常见的输出。禁止为凑满 5 条而降低门槛;空输出天数为零反而是异常信号(见验收)。

**禁止输出**:内容建议、话题、hook、结构。本 Agent 与内容生产之间隔着完整的 Gap → 学习 → 实践 → Today Signals 链路。

---

## 与 Gap Detector 的联动

action = `learn` 的信号,写入 Gap Detector 学习清单,附:来源、published_at / detected_at、以及(若 T4 已出现传播)Creator 传播起始时间。由此 Gap 清单天然携带紧迫度:T3 讨论量上升而 T4 尚未传播 = 窗口期。

action = `experiment` 的信号进入当日实验候选;实验产出于下周以 experience 身份进入 Today Signals。

---

## 未来数据流(V3 全部落地后)

```text
Official / Developer
        │
        ▼
Frontier Signal Agent ── Decision Brief(≤5/日,frontmatter Markdown)
        │
        ▼
Knowledge Gap Detector ── Learning Queue
        │
        ▼
学习 → 实践 → 经历
        │
        ▼
Today Signals → Intersection → Weekly Top Topics
```

内容永远不因「新闻发生了」而写,只因「新闻改变了工作方式、且已被实践验证」而写。

---

## 验收标准

- [ ] 连续两周每日运行,单日均 ≤ 5 条,且存在 `signal_count: 0` 的日子(空输出天数 = 0 视为凑数嫌疑,触发人工复查)
- [ ] 至少 1 条信号 Lead Time ≥ 3 天(T4 传播起始 − detected_at ≥ 72h)——验证 lead time 假设
- [ ] Detection Latency 中位数 < 24h(否则 T1/T3 抓取管道视为不合格)
- [ ] 100% 信号附一手工件 source_url;抽查无媒体转述、无预测类信号混入
- [ ] confidence 100% 符合冻结映射表(可脚本校验:工件类型 → confidence)
- [ ] 所有 frontmatter(含 health)可被脚本无错 parse(验证 Database-ready 承诺)
- [ ] Learning Queue 条目 100% 附来源与 published_at / detected_at
- [ ] 无任何输出绕过 Gap Detector 直接进入话题候选池
- [ ] Impact 评分对象始终限于冻结的四个系统;action / signal_type / time_horizon / confidence 无枚举外取值

---

## 明确不做(本提案范围外)

- T2 X 抓取(V3.1 另行提案)
- 任何形式的内容生成
- 实时推送 / 通知系统
- Database(V3.0 输出为 frontmatter Markdown;入库留待未来直接 parse,不重构)
