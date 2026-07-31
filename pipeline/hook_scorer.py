"""
pipeline/hook_scorer.py
-----------------------
Scores a hook across five dimensions using Claude.
Returns scores and pass/fail result. Does NOT write to any database —
persistence is handled by the caller (Streamlit session state in V4,
content_artifacts in a future commit).

Usage:
    from pipeline.hook_scorer import score_hook
    result = score_hook("把广告全关了，单量反而涨了")
    # result = {
    #   "luodi": 3, "universal": 2, "emotion": 2, "share": 2, "specific": 2,
    #   "total": 11, "passed": True, "rationale": "...", "model": "..."
    # }
"""

import json
from anthropic import Anthropic

from pipeline.settings import SCORER_MODEL
from pipeline import scorer_config as cfg

# ---------------------------------------------------------------------------
# Scoring rubric — anchors each dimension at 0-3 to reduce model variance.
# Written in Chinese: content is Chinese-language (XHS/Douyin), so the model
# judges in the same language context as the audience.
# ---------------------------------------------------------------------------
RUBRIC = """\
你是一个短视频/图文 hook 的评分器。对给定 hook 在以下 5 个维度各打 0-3 的整数分。
严格按锚点打分，不要客气、不要凑高分。

【落差】hook 与观众默认预期的冲突强度（反直觉程度）
  0 = 完全符合常识，无信息差
  1 = 略有新意，基本在预期内
  2 = 明显违反一个常见认知
  3 = 强烈反直觉，挑战一个被广泛默认的信念

【普世度】持有"被挑战的那个预期"的人群规模
  0 = 极小众，只有特定圈子在意
  1 = 某个细分人群
  2 = 大多数目标受众共有
  3 = 接近全民共识级的默认认知

【情绪唤起】触发的是否为高唤醒情绪（惊讶/愤怒/焦虑/好笑/强好奇）
  0 = 无情绪或低唤醒（平淡、满足、轻微感慨）
  1 = 轻度
  2 = 明确触发一种高唤醒情绪
  3 = 强烈且即时的高唤醒

【转发动机】转发它对"转发者本人"有什么好处
  0 = 转了对自己没任何好处
  1 = 弱
  2 = 有明确的社交货币 / 身份表达 / 实用价值
  3 = 强，转发几乎成了一种自我表达冲动

【具体性】数字、细节、可信度信号的密度
  0 = 全是抽象空话
  1 = 少量具体
  2 = 有具体数字或细节支撑
  3 = 高度具体，细节本身就在制造可信度与悬念

只输出 JSON，不要任何前后缀、不要 markdown 代码块。格式：
{"luodi":int,"universal":int,"emotion":int,"share":int,"specific":int,"rationale":"一句话总评，点出最弱的维度"}
"""


def score_hook(text: str, context: str = "") -> dict:
    """
    Score a hook across five dimensions. Returns a dict with scores,
    total, pass/fail result, rationale, and model name.

    Does not connect to any database.
    """
    client = Anthropic()  # API key from environment

    user_content = RUBRIC + f"\n\n待评分 hook：\n{text}"
    if context:
        user_content += f"\n\n背景（可选参考）：{context}"

    resp = client.messages.create(
        model=SCORER_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)

    scores = {
        "luodi":     int(data["luodi"]),
        "universal": int(data["universal"]),
        "emotion":   int(data["emotion"]),
        "share":     int(data["share"]),
        "specific":  int(data["specific"]),
    }
    scores["total"] = sum(scores.values())
    scores["rationale"] = data.get("rationale", "")
    scores["model"] = SCORER_MODEL
    scores["passed"] = _passes_gate(scores)
    return scores


def _passes_gate(s: dict) -> bool:
    """
    Gate logic: total score meets minimum AND both primary levers meet
    their individual floors.
    Thresholds are experimental — see scorer_config.py.
    """
    return (
        s["total"]     >= cfg.GATE_MIN_TOTAL
        and s["luodi"]     >= cfg.GATE_MIN_LUODI
        and s["universal"] >= cfg.GATE_MIN_UNIVERSAL
    )


if __name__ == "__main__":
    # Smoke test — requires ANTHROPIC_API_KEY in environment
    demo = "做了一年亚马逊，我把 80% 的广告关了，利润反而翻倍——这 3 个动作"
    print(json.dumps(score_hook(demo), ensure_ascii=False, indent=2))
