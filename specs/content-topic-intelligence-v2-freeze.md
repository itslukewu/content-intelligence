# Content Topic Intelligence V2 — 冻结范围

**日期**:2026-07-18
**状态**:Frozen v1.0(未经修订不新增范围)
**命名纪律**:本次升级不引入新系统名。仍是 Content Topic Intelligence,在既有资产上新增两个模块。"Founder Content OS" 一名弃用。

**系统第一原则**:真实经历不是一个权重,而是一张入场券。Personal Signal 不作为连续分数参与任何计算,它只回答「你有没有真正做过」。

---

## 0. 架构

```text
                Founder Knowledge / Daily Review / AI 聊天记录
                                   │
                                   ▼
                          Today Signals(已有,周报)
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
  Slow Signal                Fast Signal              Personal Evidence
  Creator Intelligence       AI 新闻(每日,手动)       evidence_level 标注
  (周二 / 周五)              V1 不开发                 (见接口冻结 §I-1)
        │                          │
        │                          └────────────┐
        ▼                                       ▼
              Intersection Engine ← 新模块①      Knowledge Gap Detector ← 新模块②
                       │                                │
                       ▼                                ▼
              Weekly Top 10 Topics                 学习清单(不产内容)
```

**数据流规则**:Fast Signal 的输出永远不直接进入话题候选池。合法去向仅两个:(a) Gap Detector 学习清单;(b) 触发当天真实实验,实验产出下周以 experience 身份进入 Today Signals。

**Architecture Rule(冻结)**:任何新增模块必须同时具备**输入定义、输出定义、验收标准**三项,缺一不得进入 Scope。此规则适用于未来一切提案(Style Engine、Creator DNA、Visual Embedding 等一律先过此关)。

---

## Phase 1 — Creator Intelligence 信号质量修复

**原则**:先把每一层做好,再允许下一层依赖它。Intersection 在 Phase 1 验收前不动工。

必须完成的四项:

1. **Topic Clustering**
   - 合并重叠 n-gram 为单一 canonical 主题(当前 "fable 5's / 5's leaked / leaked system…" 占据 10 席中 8 席,实为同一帖子族)。
   - Topic Intelligence 榜单加最小样本门槛:count ≥ 3 才可上榜;count < 3 的单帖话题移入独立的 "Outlier Posts" 附录,不参与排序。

2. **Followers**
   - 修复 follower 抓取;若数据源确实拿不到,则在 Health Block 中显式声明 degraded(禁止静默回退到 creator-baseline 后仍宣称跨账号归一化)。

3. **Brand Fit Score**
   - 使用冻结 Prompt(见接口冻结 §I-2),对每条帖子相对 Luke 定位打分。
   - 直接后果:lead-magnet 型内容(comment-to-DM)即使 velocity 高,Brand Fit 应显著拉低其对「值得写」的贡献。

4. **CTA Bias 校正**
   - 当前榜首几乎全是 comment-gated lead magnet,反映的是 CTA 机制而非内容质量。
   - 处理方式:hook / CTA 对总分的贡献设上限,并将「互动被 CTA 机制驱动」单列为可见标签,供 Intersection 阶段降权。

**通用要求**:每次运行输出符合冻结 Schema 的 Health Block(见接口冻结 §I-3)。阅读顺序纪律:任何一次运行,先看 Health,再看 Topic。

**验收标准**(全部满足才进入 Phase 2;ID 供 Gate 一一引用,见附录 G):
- [ ] **P1-A1** 主题榜单无重叠 n-gram 重复(quality:script)
- [ ] **P1-A2** Topic Intelligence 榜单全部 count ≥ 3(quality:script)
- [ ] **P1-A3** followers 有值,或 Health Block 明确标注 degraded(quality:script)
- [ ] **P1-A4** 每条帖子带 Brand Fit 分数,冻结 Prompt 产出(interface:script)
- [ ] **P1-A5** Health Block 随每次运行输出且符合 Schema(interface:script)

---

## Phase 2 — Intersection Engine

**形态**:一个 prompt / 一步 CLI。无 Dashboard,无 Database,无 Scheduler。

**输入**:
- Founder Weekly(现有 Content Topic Intelligence 周报,含 evidence_level)
- Creator Weekly(Phase 1 修复后的 Creator Intelligence 输出)

**流程**:

```text
Candidate Topics
      │
      ▼
Evidence Gate(硬门槛,枚举路由,不打分)
  evidence_level ∈ {artifact, experience} → 进入排序
  evidence_level ∈ {learning, idea}       → 转入 Gap Detector
      │
      ▼
排序 = Trend × Brand Fit × Novelty
      │
      ▼
Weekly Top 10 Topics(每条附:来源证据、市场信号出处、建议角度一句话)
```

**验收标准**:
- [ ] **P2-A1** 连续两周输出 Top 10,且 Luke 主观判断其中 ≥3 条「确实值得写」(quality:**manual** — Gate 只能记录 pending/confirmed,不得自动 PASS)
- [ ] **P2-A2** 无任何 learning / idea 话题绕过 Gate 进入榜单(quality:script)

---

## Phase 3 — Knowledge Gap Detector

**形态**:一个 diff。

**逻辑**:出现在 Market Signals(Slow 或 Fast)中、但 Founder Knowledge / Daily Review / 聊天记录中无对应内容的话题,以及被 Gate 拦下的 learning / idea 话题 → 输出「值得学习」清单。

**输出**:学习清单,不产内容。流程强制为:不知道 → 学习(learning)→ 实践(experience)→ 形成观点 → 输出内容。

**验收标准**:
- [ ] **P3-A1** 清单中每项附市场信号出处(哪些 creator、何时开始讲)(interface:script)
- [ ] **P3-A2** 区分「已学未实践」(learning,差一步实验)与「完全空白」(未接触)(interface:script)
- [ ] **P3-A3** 不生成任何内容建议、hook 或结构(quality:script)

---

## I. 接口冻结(Interfaces)

以下三项属于接口,与 Scope 同时冻结。后续所有 Prompt、CLI、测试、Agent 必须复用,不得各自定义。

### I-1. evidence_level 枚举

```yaml
evidence_level:
  artifact:
    definition: 已有可展示产出
    examples: [代码, SOP, Dashboard, JSON, Workflow, 已发布内容]
  experience:
    definition: 已完成实践
    examples: [实验, 失败, 决策, 客户案例]
  learning:
    definition: 已阅读或学习,尚未实践
    examples: [论文, 视频, 课程, 文档]
  idea:
    definition: 纯设想
    examples: [未验证的观点, 计划中的功能]

routing:
  intersection: [artifact, experience]
  gap_detector: [learning, idea]
```

**迁移说明**:此枚举取代旧三档(产出物/经历/纯想法)。上游 Today Signals 抽取 Prompt 需同步改为输出四值——旧「纯想法」拆分为 learning 与 idea。下游行为不变(两者都进 Gap),拆分的价值在于 Gap Detector 可区分「差一步实验」与「完全空白」。

### I-2. Brand Fit Prompt(冻结)

```text
你是 Brand Fit 评审。只回答一个问题:这条内容是否符合以下定位?

定位(仅此五项):
- AI-first Founder
- System Builder
- Building in Public
- 长期可复用(evergreen,非时效性)
- 系统思维(框架/流程/方法论,非孤立技巧)

评分 0-10,并给出一句理由。

禁止参考(出现即视为评审无效):
- 点赞、播放、评论、分享等任何互动数据
- 是否热门、是否上榜、是否病毒式传播
- 作者的粉丝量或影响力
```

**冻结理由**:Brand Fit 是最容易随模型更换而漂移成 Popularity 的分数。Prompt 固定后,换模型只影响执行质量,不改变评审对象。

### I-3. Health Block Schema(冻结)

```yaml
health:
  run_at: <ISO 8601>
  creator_count: <int>
  posts_analyzed: <int>
  followers:
    status: ok | degraded
    missing_creators: [<username>, ...]
  topic_cluster:
    before: <int>          # 聚类前原始主题数
    after: <int>           # 聚类后 canonical 主题数
  cta_gated_posts_pct: <float>
  topics_count_lt3_pct: <float>
  warnings: [<string>, ...]
```

---

## 运行节奏

| 数据源 | 频率 | V1 实现方式 |
|---|---|---|
| Creator Intelligence(Slow) | 每周二、周五 | 现有 Apify 管道,手动触发 |
| AI 新闻(Fast) | 每日 | **不开发**。人工阅读,手动记入 Daily Review |
| Intersection Engine | 每周一次 | Prompt / CLI,手动触发 |
| Gap Detector | 随 Intersection 运行 | 同上 |

---

## 冻结区(V1 稳定前一律不做)

- Daily Scheduler / 任何自动定时
- Topic 评分公式(Personal × Trend × … 的乘法公式)
- Content Builder(多平台版本自动生成:Carousel / Reel / Threads / LinkedIn / Newsletter)
- Auto Carousel / Auto Script / Podcast
- Dashboard / Database
- Fast Signal 自动化(新闻抓取管道)

---

## 解冻条件与终止条件

**解冻条件**:Phase 1–3 全部通过验收,且 Intersection 连续四周输出被实际采用的话题。

**终止条件(Feedback Loop)**:若 Intersection 连续四周未产生任何被实际采用的话题,立即暂停一切新增功能,进入全链路诊断。诊断不预设故障层——按 Health Block 数据依次排查:(1) Creator Intelligence 信号质量是否退化;(2) Evidence Gate 是否过严(候选池是否长期为空);(3) Today Signals 是否过薄(本周真实产出不足)。定位故障层并修复后,重新计时。

---

## 附录 G — Gate 约定(2026-07-18 增补,不改变任何 Scope)

Gate 是本 spec 解锁条件的执行器:**Spec 定义验收,Gate 自动验证,Implementation 只有通过 Gate 才算完成**。已有实例:creator gate(检查 canonical_topics / brand_fit 等可验收产物,验证 Contract 而非 Implementation)。

**两层结构**:
- **Interface Gate**:回答「产物在不在」——字段存在、Schema 可 parse。
- **Quality Gate**:回答「产物合不合格」——逐条对应本 spec 的验收标准(如压缩比、count ≥ 3、重复检测)。

**Spec–Gate 一一对应(强制)**:
1. 本 spec 每条验收标准带稳定 ID(P1-A1 … P3-A3);Gate report 的每个检查项以同一 ID 为 key。
2. 双向完整性可脚本校验:spec 中每个 ID 必须在 gate report 出现,gate report 不得出现 spec 之外的 PASS 项。Spec 改,Gate 必须同轮改,脱节即 Gate 自身 FAIL。
3. 每条标准标注 `script` 或 `manual`。**manual 项(如 P2-A1 的主观判断)Gate 只能记录 pending / confirmed(confirmed 须由 Luke 显式标记),永远不得自动 PASS**——否则 Gate 通过将不再等价于 spec 验收。
4. 解锁判定 = 对应 Phase 全部 ID 为 PASS/confirmed。Gate report 顶部输出单行结论(如 `V2.1 unlocked: no`)。

**反过度建设**:V1 阶段每个 Phase 一个独立 gate 脚本即可,不建 Gate 框架;模式在 ≥3 个 gate 落地后再抽象。
