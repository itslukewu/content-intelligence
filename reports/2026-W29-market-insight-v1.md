# Market Insight Report — V1(第一版)

**生成**:2026-07-18 · 数据:creator_intelligence_report(227 帖 / 12 创作者 / 总播放 14.05M)
**方法**:份额与计数由脚本计算;RP = relative_performance(相对创作者自身基线的倍数),所有入选证据须 RP > 1;证据分级沿用三档 **Confirmed(≥3 独立创作者)/ Emerging(2)/ Weak(1)**

```yaml
health:
  posts: 227
  creators: 12
  total_views: 14,047,600
  topic_min_count: 3          # count<3 不参与供需排序
  followers: degraded          # 全量缺失,未做跨账号归一化
  provenance: post_content     # 无评论数据,全部为 creator-mediated 证据
  warnings:
    - pain_points 直接证据薄弱(帖子端痛点多以问题框架间接表达)
```

---

## 1. Top Pain Points(痛点)

直接的痛点表述在帖子端很少(这是纯帖子数据的天然盲区,诚实标注),但从问题框架和高 RP 内容可反推三个核心痛点:

- **不知道如何把 Claude/AI 用出实际结果**(不会用 → 用不好 → 变不了现)。〔Confirmed:sabrina(15+ 问题式帖)、nick(Skills/Plugins 教程 4.8x)、leadgenman("Why is Claude that good" 1.3x)〕
- **内容做不出增长**:hook 写不好、没有内容规划。〔Emerging:kallaway("hook 科学上不可跳过" 6.5x;"30 分钟规划 30 天内容" 9.3x)、lazymillionaire(增长方法 39x)〕
- **想构建但怕出错 / 不敢上线**。〔Weak→见 Block 4 resistance,shrug.manny 双帖〕

## 2. Emerging Needs(新出现的需求,近两周首现且 >50K 播放)

- **Claude Code 生态配置**:claudecodesetup / claudeplugins 标签 7 月 5 日首现(50.8K),nick 的 Skills / Plugins 系列 RP 1.3–4.8x。〔Emerging〕
- **ChatGPT/AI 用于自我反思与心理**:chatgptprompts + psychology 7 月 17 日首现(64.7K),sabrina "self-reflection / limiting beliefs" 系列 RP 1.4–2.2x。〔Weak,单创作者〕
- **OpenAI 发布追踪**:chatgpt_partner 7 月 11 日,830K 播放单帖。〔Weak,且属新闻型——按你的规则只配进学习/关注,不配做话题〕
- **Claude Cowork 入门**:sabrina masterclass 3.0x。〔Weak〕

## 3. Repeated Questions(反复出现的问题框架)

来自 question-led hook(注意:这是创作者提的问题框架,非受众原声):

- How do you **make money with Claude / with AI**?〔sabrina 5.2x、raycfu "$7k/month" 2.5x — Emerging〕
- How do I **use Claude to run my social media / automate posts**?〔sabrina 3.0x ×2、kallaway "social media machine" 14.4x — Emerging〕
- How do **Claude connectors / Skills / Plugins work**?〔sabrina 2.6x、nick 4.8x/1.3x — Emerging〕
- What **AI should I use to build apps / write**?〔sabrina 3.1x ×2 — Weak〕

## 4. Fears & Objections(阻力)

- **fear**:"Everyone says vibecoding is dangerous"(shrug.manny,**9.7x**);"Everyone thinks launching an app is dangerous"(1.4x)。〔Weak 档但 RP 极高——恐惧真实存在,回应它的内容被市场重奖〕
- **misconception**:"Everyone's still perfecting their prompts. That's about to feel outdated"(leadgenman,2.1x)——受众隐约意识到「调 prompt」不是终局。〔Weak〕
- **objection**(隐含):AI 工具清单类内容 avg RP 仅 1.18x(见 Block 6)——市场开始对「又一个工具推荐」免疫。

## 5. Dreams & Aspirations(渴望的结果)

高 RP 帖子售卖的承诺,即受众用互动投票认可的梦想:

- **一个人 + 自动化 = 规模**:"turn Claude into a social media machine"(14.4x)、"$7k/month YouTube automation"(2.5x)。〔Confirmed:kallaway、raycfu、sabrina〕
- **快速可见的增长**:"10,000 followers in 3 weeks"(39x)、"30 天内容 30 分钟规划完"(9.3x)。〔Emerging〕
- **摆脱重复人生 / 自由**:thedankoe "You weren't meant to repeat the same day for 40-60 years"(1.8x)、"change your life in 1 day"(3.3x)。〔Weak〕

## 6. Hidden Insights(Supply Gap,脚本计算)

`supply_gap = engagement_share − frequency_share`(市场奖励什么 − 创作者供给什么):

| 主题 | 帖数 | 创作者 | 供给份额 | 互动份额 | Gap | 档位 |
|---|---:|---:|---:|---:|---:|---|
| vibecoding / AI 编程 | 31 | 4 | 13.7% | 32.8% | **+19.2%** | Confirmed |
| claude 深度使用 | 22 | 5 | 9.7% | 18.4% | **+8.7%**(avg RP 13.4x) | Confirmed |
| startup / 创业构建 | 12 | 2 | 5.3% | 11.4% | +6.1% | Emerging |
| make money with AI | 6 | 2 | 2.6% | 6.7% | +4.1% | Emerging |
| 泛社媒/内容技巧 | 25 | 5 | 11.0% | 6.8% | **−4.2%** | Confirmed(过度供给) |
| AI 工具清单 | 14 | 3 | 6.2% | 3.5% | −2.7%(avg RP 1.18x) | Confirmed(过度供给) |

三条洞察(LLM 解释,数据在上):

1. **市场要的不是工具,是系统**:AI 工具清单过度供给(−2.7%,RP 1.18x),而 claude 深度工作流严重供不应求(+8.7%,RP 13.4x)。"把 Claude 变成 machine" 的系统叙事(14.4x)远胜 "推荐 10 个 AI 工具"。
2. **vibecoding 是当前最大的供给缺口**(+19.2%),且与最高单条 resistance("vibecoding is dangerous" 9.7x)同主题——**教人安全地构建**是缺口中的缺口:需求最大、恐惧最强、无人认真回应。
3. **离开利基即坠落**:lifestyle 类标签(corporategirlie / dancer / 5to9 / career)RP 全部 0.6–0.9x。利基创作者发泛内容,市场立刻用脚投票。

## 7. Content Opportunities(推导:primary_basis = pain / hidden insight)

- **"安全构建" 缺口**〔basis: HI-2 + Fear-1〕:回应 "vibecoding is dangerous" 的方法论内容,几乎无人供给。
- **Claude 系统化工作流**〔basis: HI-1 + Q-2/Q-3〕:不是介绍 Claude,而是展示「Claude 作为系统组件」的真实构建过程。
- **"分析了 N 条爆款" 元内容**〔basis: HI-1 + Pain-2〕:kallaway 的方法论拆解类内容稳定高 RP(6.5x / 9.3x),市场为「基于数据的 how」付费。

## 8. Product Opportunities(→ 业务决策,不进内容管道)

- 反复出现 "How do connectors / Skills / Plugins work"(Block 3)→ **Claude Code 配置/模板类资产**(setup 模板、skill 包)有需求信号。〔Emerging〕
- "30 天内容 30 分钟" 9.3x + 你正在构建的这套系统本身 → **Content Intelligence 作为产品/服务**的需求侧验证。〔Emerging〕

## 9. Evidence Sources

12 位创作者 / 227 帖 / 14.05M 播放;引用帖子全部 RP > 1;份额与计数可由脚本从原始 JSON 复算;无评论数据,全部证据为 creator-mediated(创作者声称 × 市场互动验证)。

## 10. Evidence Strength 总评

- Confirmed:HI-1(工具→系统)、HI-2(vibecoding 缺口)、Asp-1(一人+自动化)、Pain-1(不会把 AI 用出结果)
- Emerging:Claude Code 生态需求、money-with-AI 问题框架、增长渴望
- Weak:自我反思类、Cowork、自由叙事——**不得单独支撑选题**

---

# Intersection — 结合你的真实产出选题(V1)

入场券检查:每个话题必须有你的 artifact / experience 支撑。

## ★ Top 5 话题

**T1|"所有人都说 vibecoding 危险。我的答案:给 AI 立规矩——Frozen Spec + Gate"**
市场:HI-2(+19.2% Confirmed)× Fear-1(9.7x)。你的入场券:**今天刚建成的 Gate 系统**(截图里那句 "V2.1 unlocked: no")、四份冻结规格、"Don't infer, verify" 原则。〔artifact ✓〕这是缺口中的缺口,且你的证据是独家的。

**T2|"我用 AI 分析了 227 条 AI 创作者爆款,发现市场根本不奖励工具推荐"**
市场:HI-1(Confirmed)× Pain-2;方法论拆解类内容稳定高 RP。你的入场券:**今天这份分析本身**(supply gap 表格直接做 carousel 素材)。〔artifact ✓〕

**T3|"一个人 + 一群 Claude agent,经营 4 个 Amazon 品牌"**
市场:Asp-1(Confirmed,一人+自动化)× vibecoding/agents 缺口。你的入场券:**12-agent listing 管道、图片管道**,真实跑在真实生意上。〔artifact ✓〕降低设计感、提高真实性——实拍系统运行画面即封面。

**T4|"别再优化 Prompt 了。把 Claude 变成系统"**
市场:Misconception-1(prompt 调优将过时)× HI-1 × "machine" 叙事 14.4x。你的入场券:Evidence Gate / 冻结接口 / 枚举优于自由文本——你的整套「确定性优先」实践。〔artifact ✓〕与你既定首帖「定义目标函数,而不是向 AI 要最佳答案」同一叙事线,可做系列。

**T5|"Obsidian + Claude Code:我的第二大脑真实工作流"**
市场:Second Brain 主题 x2 帖 avg 362K(Emerging,样本小,诚实标注)。你的入场券:**你的 PKM 系统**(Obsidian + Claude Code 自动化)。〔artifact ✓〕

## → Learning Queue(市场热、你未实践或未沉淀的)

- **Claude Code Skills / Plugins / Cowork**:claudecodesetup 7 月 5 日首现,nick 系列 4.8x,connectors 问题反复出现。你日常在用 Claude Code,但 Skills/Plugins/Cowork 若尚未系统实践 → 先实验,产出后自动升级为 T 级话题(且大概率是下一个 T1 级窗口)。
- ChatGPT × 心理/自我反思(7 月 17 日新芽):与你定位相关性弱,观察即可。

## 明确不选

- OpenAI 发布追踪类(830K 播放但纯新闻,无入场券,违反 Fast Signal 规则)
- 泛社媒技巧、AI 工具清单(Confirmed 过度供给)
- 任何 lifestyle 泛内容混入专业号(HI-3:离开利基即坠落)
