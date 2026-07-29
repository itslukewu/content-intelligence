# Insight Layer + Opportunity Layer — V2.1 提案

**日期**:2026-07-18(rev 3)
**状态**:**Parked — 解锁条件 = V2 Phase 1 四项修复全部通过验收**
**性质**:Creator Intelligence 的输出层扩展(非新 Agent)。本提案按 Architecture Rule 补齐输入 / 输出 / 验收三项。

**分层原则**:观察与决策分层。Insight Layer 回答「市场发生了什么」(纯观察);Opportunity Layer 回答「基于观察应该做什么」(推导)。

**证据哲学**:不抓评论。评论是 self-reported preference(用户说想要什么),帖子表现是 revealed preference(市场用互动行为投了什么票)——后者更可靠。V2.1 以 revealed preference 为唯一证据基础。

**概念定位**:Creator 是传感器,Market 才是输出。本层分析的对象不是创作者,而是市场。**命名暂不变更**(遵守 V2 命名纪律,冻结期内不引入新系统名);"Market Insight Layer / Founder Market Intelligence" 作为候选名记录于此,待 V2 解冻或 V2.1 交付时统一评估重命名。

---

## 架构位置

```text
Creator Intelligence(Phase 1 修复后)
   Posts(现有数据,无新输入)
        │
        ▼
   Insight Layer(纯观察)
        │
        ├──→ Audience Intelligence Agent(需求类 Block 作为新 source 汇入)
        │
        ▼
   Opportunity Layer(推导)
        ├──→ Content Opportunities → Content Topic Intelligence V2(Intersection 输入)
        └──→ Product Opportunities → 业务决策(不进内容管道)
```

---

## 输入

Phase 1 修复后的 Creator Intelligence 输出,**无新增数据源**:聚类后 canonical topics、帖子全文(title + text + hook 类型 + CTA 类型)、互动数据(views / likes / relative_performance)、Brand Fit、Health Block。

**依赖关系**:唯一前置条件是 Phase 1 验收——今天的 227 条 JSON 即可作为开发测试集。

---

## 证据来源声明(冻结)

所有 Insight 均为 **creator-mediated**:观察到的是「创作者声称受众想要什么,且该声称被互动数据验证」,而非受众直接发言。三个补偿机制:

1. **互动验证闸**:每条 insight 的支撑帖子必须 relative_performance > 1.0(跑赢创作者自身基线),排除「说了但市场没买账」的声称。
2. **跨创作者独立性**:evidence_strength 按独立创作者数计档(复用 Audience Agent 三档:Confirmed ≥3 / Emerging 2 / Weak 1)。
3. **来源标注**:每条 insight 标注 `provenance: post_content`。若 question_frames / resistance 两个 Block 连续两轮停留在 Weak 档,即为「纯帖子证据不足」的量化信号,届时再提案评论抓取(V2.2)——用档位分布数据决定,不用直觉。

---

## 输出 — Insight Layer(纯观察)

固定 Schema(frontmatter Markdown,Database-ready):

```yaml
insights:
  pain_points: []          # 1. 帖子明确针对且获超额互动的困难
  emerging_needs: []       # 2. 新近出现的主题需求(近 2 周首现或份额陡增)
  question_frames: []      # 3. question-led hook 中反复出现的问题框架
                           #    (rev 3 改名:无评论数据,问题来自 Creator 而非 Audience,
                           #     旧名 repeated_questions 会误导证据来源)
  resistance: []           # 4. 帖子正面回应的阻力,subtype 枚举:
                           #    fear(AI 会取代我)| objection(AI 不可靠)| misconception(误解)
  aspirations: []          # 5. 高互动帖子售卖的结果承诺
  hidden_insights: []      # 6. Supply Gap 洞察(见公式)
  evidence_sources: {}     # 7. 全局证据清单(creators / posts 计数与出处)
  # 8. 每条 insight 内嵌 evidence_strength
```

每条 insight 的字段:

```yaml
- statement: <一句话观察>
  evidence_strength: confirmed | emerging | weak
  provenance: post_content
  subtype: <仅 resistance 使用:fear | objection | misconception>
  supporting:
    creators: <int>
    posts: <int>
    min_relative_performance: <float>   # 须 > 1.0
    first_seen: <ISO 8601>
  examples: [<帖子标题短引 ≤2 条>]
```

**接口复用规则(冻结)**:evidence_strength 采用 Audience Agent 三档,计档单位 = 独立创作者;需求类 Block 输出格式与 Audience Agent signal 格式兼容,作为其新 source 汇入。

**Hidden Insight = Supply Gap 公式(冻结,Deterministic First)**:

```text
supply_gap(topic) = engagement_share(topic) − frequency_share(topic)

frequency_share  = 该主题帖子数 / 全部帖子数(创作者在供给什么)
engagement_share = 该主题互动加权份额 / 全部互动(市场在奖励什么)
```

- **脚本计算 gap 并排序;LLM 只负责解释为什么**,不负责判定什么是 insight。
- gap > 0 = 供给缺口(讲的人少,讲了就爆);gap < 0 = 过度供给(人人在讲,市场不买账)。两个方向都入选,按 |gap| 排序。
- 无 supply_gap 数据支撑的洞察降级为 idea,不得进入 Insight Layer。

---

## 输出 — Opportunity Layer(推导)

```yaml
opportunities:
  content:               # → 进入 Intersection 候选(仍须过 Evidence Gate)
    - gap: <供给缺口 / 无人解释为什么>
      primary_basis: [<pain_points 或 hidden_insights 的引用,≥1>]
      supplementary: [<其他 Block 引用,可选>]
  product:               # → 业务决策,不进内容管道
    - signal: <反复出现的需求信号>
      primary_basis: [<pain_points 或 hidden_insights 的引用,≥1>]
      supplementary: [<其他 Block 引用,可选>]
```

**推导规则(冻结)**:
- 每条 opportunity 的 **primary_basis 必须引用 ≥1 条 confirmed/emerging 级的 pain_points 或 hidden_insights**。
- aspirations / resistance / question_frames / emerging_needs 只能作 supplementary,不得单独支撑——「很多人想要自由 → 做个产品」这类推导链太弱,aspiration 只说明方向,pain point 和 supply gap 才说明切入点。resistance 作为 supplementary 对 objection-handling 类内容尤其有用。
- Content opportunity 进入 Intersection 后**仍受 Evidence Gate 约束**——市场有 gap 不等于你有入场券。
- Product opportunity 的消费方是业务决策,不进内容管道;两条下游互不越界。

---

## Health 扩展 — Coverage Block(冻结)

Insight 输出容易「看起来完整」,Coverage 暴露每个 Block 的样本覆盖度:

```yaml
health:
  coverage:                    # 各 Block 支撑帖子数 / 总帖子数
    pain_points: <float>
    emerging_needs: <float>
    question_frames: <float>
    resistance: <float>
    aspirations: <float>
    hidden_insights: <float>
  posts_total: <int>
  posts_cited: <int>           # 至少支撑一条 insight 的帖子数
  warnings: [<string>, ...]
```

阅读纪律不变:先看 Health(含 Coverage),再看 Insight。Coverage < 10% 的 Block 自动附 warning,提示该 Block 的结论建立在边角样本上。

---

## 验收标准

- [ ] 100% insight 的 supporting.min_relative_performance > 1.0
- [ ] evidence_strength 100% 按独立创作者数计档,与 Audience Agent 规则一致(脚本校验)
- [ ] 100% insight 标注 provenance;resistance 条目 100% 带 subtype 枚举值
- [ ] 100% hidden insight 附 supply_gap 数据,且 frequency_share / engagement_share 可由脚本从原始 JSON 复算;榜单顺序 = 脚本排序,非 LLM 排序
- [ ] 100% opportunity 的 primary_basis 引用 ≥1 条 confirmed/emerging 级 pain_points 或 hidden_insights
- [ ] Coverage Block 随每次运行输出;coverage < 10% 的 Block 附 warning
- [ ] 需求类 Block 输出可被 Audience Intelligence Agent 无转换消费(格式兼容性测试)
- [ ] Schema 稳定,frontmatter 可无错 parse
- [ ] 连续两轮后复盘 question_frames / resistance 档位分布(V2.2 评论抓取的决策依据)

---

## 明确不做

- 评论抓取(V2.2 候选,由档位分布数据决定是否提案)
- 冻结期内重命名(Market Insight Layer 等候选名仅记录,待 V2 解冻统一评估)
- 内容生成(hook / 结构 / 多平台版本)
- LLM 主观 confidence 打分
- 在 Phase 1 验收前动工
