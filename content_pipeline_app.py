"""
内容流水线 · Content Pipeline v3
=================================
pip install streamlit anthropic requests
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run content_pipeline_app.py
"""

import os, re, json, sqlite3, glob
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st
from anthropic import Anthropic

try:
    import requests as req_lib
except ImportError:
    req_lib = None

# ================================================================
# CONFIG — 改这里就能换方向，不用动下面的 prompt
# ================================================================
MODEL = "claude-sonnet-4-6"

# DB_PATH and SCORER_MODEL are defined centrally in pipeline/settings.py.
# This app imports them directly — do not redefine here.
from pipeline.settings import DB_PATH
from pipeline.constants import (
    TOPIC_TYPES, STRUCTURES, HOOK_PATTERNS, HOOK_PATTERN_DEFINITIONS,
    PLATFORMS, FORMATS,
)

# ⬇️ 你的内容方向，所有 prompt 都引用这个变量
CONTENT_DIRECTION = """
我是一个 solo entrepreneur / AI-powered operator，同时运营多个品牌。
我的内容覆盖以下方向（不限于此）：
- Amazon / 跨境电商运营实战（PPC、Listing、数据诊断）
- AI Agent / AI Operator / 自动化工作流
- 创业复盘 / 个人商业认知
- 产品增长 / 用户体验
- 中国产业政策与趋势分析
- 任何我有真实经验和判断的领域
""".strip()

MODULES = [
    "电商运营诊断",
    "AI Agent / Operator",
    "创业复盘",
    "产品增长",
    "个人商业认知",
    "趋势 / 政策分析",
    "其他",
]

# ================================================================
# PROMPTS
# ================================================================
HOOK_SYS = f"""你给一个有真实创业和运营经验的中国创业者写短视频开头 hook。

他的内容方向：
{CONTENT_DIRECTION}

语感要求：像他在跟朋友吃饭时突然说了一句让人停筷子的话。
- 中英混用自然：bid、listing、CTR、ACOS、agent、workflow 这些直接说英文
- 短、直接、有判断，不铺垫
- 带冲突、痛点、反常识或损失感

禁止：「今天我们来聊聊」「你有没有想过」「很多人不知道」「答案可能出乎你的意料」
「在当今时代」「不得不说」「本质上」「说白了」「让我来告诉你」「随着…的发展」

好的 hook 例子：
- 你的广告不是没问题，是它吸引来了错误的人。
- CTR 高不是好消息，如果 CVR 很低，你的 listing 可能在骗人。
- 先别急着降 bid。
- 你每天重复做的那件事，正在被 Agent 替掉。
- 这个政策不是利好，是淘汰加速器。

只输出 JSON 数组，不要任何解释或 markdown 代码块。
`type` 字段必须从以下枚举值中选一个（直接输出英文值，不要翻译）：
{HOOK_PATTERN_DEFINITIONS}"""

SCRIPT_SYS = f"""你给一个有真实创业和运营经验的中国创业者写 45-60 秒短视频口播稿。

他的内容方向：
{CONTENT_DIRECTION}

## 声音特征
- 像语音备忘录，不像文章。短句为主，一句一个意思。
- 中英混用很自然：专业术语直接说英文，不翻译。
- 敢下判断，不用「可能」「也许」「在某种程度上」对冲。
- 允许不完整的句子、口语停顿（「等一下」「你想想」「对吧？」）、反问。
- 说人话。不要播音腔，不要公众号腔，不要知乎腔。

## 禁止使用的 AI 味词汇和句式（出现任何一个就算失败）
本质上、其实、简单来说、换句话说、值得注意的是、不得不说、众所周知、毋庸置疑、
归根结底、说白了、一言以蔽之、在当今时代、随着…的发展、不可否认、事实上、
首先…其次…最后…、让我们来看看、接下来我们聊聊、今天我们来聊、
这意味着什么呢？让我来告诉你、你有没有想过、答案可能出乎你的意料、
这背后的逻辑是、深度解析、全面剖析、底层逻辑、颠覆认知、赋能、闭环、抓手、
打法、沉淀、拉齐、对齐

## 结构（六段，过渡要像说话，不要像论文大纲）
Hook -> Problem -> Insight -> Example -> Action -> Closing
段与段之间不要用「接下来」「所以」「那么」这种机械连接词。直接切。

## 参考范例（模仿语感，不要复制内容）
---
你的广告不是没问题，是它吸引来了错误的人。

很多卖家看到 CTR 高，觉得主图不错。但 CTR 高、CVR 低，这不是好消息。

用户愿意点进来，但进来之后不想买。这就叫 promise mismatch。
你的主图、标题、广告词，给了用户一个期待。但你的价格、review、详情页，没有兑现。

举个例子。主图看起来像 premium product，点进去 review 很少，详情页很普通，价格还比竞品高。用户直接退出。

这时候不要第一反应去降 bid。先检查：主图承诺了什么？标题承诺了什么？详情页兑现了没有？价格和 review 撑不撑得住这个定位？

记住一句话：CTR 负责吸引，CVR 负责验证承诺。如果 CTR 高但 CVR 低，你要修的不是广告，是承诺和现实之间的落差。
---

## 如果提供了参考模版
如果用户附带了参考模版（来自模版库的结构分析），请参考该模版的结构和节奏来写，但内容和语感仍然是你自己的。不要照搬模版的用词。

## 输出格式（纯文本，不要 JSON，不要 markdown）
TITLE: 标题
COVER: 封面文字（10字以内）
CTA: 结尾引导一句
SCRIPT:
[Hook] ...

[Problem] ...

[Insight] ...

[Example] ...

[Action] ...

[Closing] ..."""

VISUAL_SYS = f"""你是一个短视频视觉导演。

内容方向：
{CONTENT_DIRECTION}

风格：专业、干净、有商业分析感，适合小红书 / TikTok / YouTube Shorts。

根据提供的口播稿，输出逐镜拍摄方案。要求：
- 每 3-5 秒一个镜头
- 给出可实际执行的方案，不要太复杂
- 镜头类型：正面近景 / 屏幕录制 / 手机俯拍 / 切换 B-roll
- 每个镜头给出：画面描述、屏幕字幕、语气/表情、时长

严格按以下纯文本格式输出，不要 JSON，不要 markdown：

STYLE: 整体视频风格一句话
SCENE: 拍摄场景建议
COVER_DESIGN: 封面设计建议
SHOTS:
【镜头1】时长：Xs
画面：...
字幕：...
语气：...
B-roll：...（如适用）

【镜头2】..."""

SIGNAL_SYS = f"""你是一个内容信号收集 Agent。从原始素材中提取可以变成爆款短视频的信号。

内容方向：
{CONTENT_DIRECTION}

分析维度：
1. 用户真实痛点
2. 反常识观点
3. 传播冲突（大多数人以为 X，其实 Y）
4. 内容形式建议

纯文本格式输出，不要 JSON，不要 markdown 代码块：

===信号 1===
选题: 一句话选题
痛点: 用户的真实痛点
冲突: 传播冲突点
模块: （从以下选一个：{' / '.join(MODULES)}）
优先级: 高 / 中 / 低
理由: 为什么值得做
结构: 最适合的内容结构（从以下选一个：痛点解决型 / 观点反转型 / 过程记录型 / 数据说话型 / 身份认同型）

===信号 2===
...

最多 5 个信号，按优先级排列。选题要具体到能直接生成 hook。"""

TEMPLATE_ANALYZE_SYS = f"""你是一个爆款内容结构分析师。你的任务是拆解一条短视频或图文的内容结构，提取可复用的模版。

分析维度：
1. Hook 类型和手法（反常识/恐惧/损失/结果/身份/对比/诊断/案例/趋势/错误认知）
2. 整体结构（比如：Hook→痛点→方案→案例→CTA，或者 故事→转折→判断→行动）
3. 节奏特征（信息密度、停顿位置、转折位置）
4. 语言风格（口语/书面、中英混用程度、长短句比例）
5. 为什么这个结构有效
6. 这个模版适合什么类型的选题

纯文本格式输出：

TEMPLATE_NAME: 2-6个字的模版名称（比如「数据异常诊断型」「认知反转型」「我以前以为型」）
HOOK_TYPE: hook 类型
STRUCTURE: 用箭头表示结构（如：数据异常 → 常见误判 → 真正原因 → 检查顺序 → 一句话总结）
RHYTHM: 节奏特征
STYLE: 语言风格
WHY_IT_WORKS: 为什么有效
GOOD_FOR: 适合什么选题（逗号分隔）
ORIGINAL_HOOK: 原内容的 hook（一句话）
FULL_BREAKDOWN: 逐段拆解（标注每段在做什么、为什么放在这里）"""

TEMPLATE_RECOMMEND_SYS = """你是一个内容模版推荐 Agent。根据用户的选题和 hook，从模版库中推荐最匹配的模版。

评判标准：
1. 选题类型是否匹配模版的适用范围
2. Hook 类型是否和模版的 hook 手法一致
3. 选题的传播冲突是否适合该模版的结构

纯文本格式输出，不要 JSON，不要 markdown：

===推荐 1===
模版: 模版名称
匹配度: 高/中
理由: 为什么这个模版适合这个选题
改编建议: 用这个模版的话，具体怎么套

===推荐 2===
...

最多推荐 3 个。如果没有合适的，直接说「模版库中没有高匹配的模版，建议自由发挥」。"""

# ================================================================
# FILE READING HELPERS
# ================================================================
def read_uploaded_files(files):
    chunks = []
    for f in files:
        name = f.name.lower()
        try:
            raw = f.read()
            if name.endswith(".json"):
                data = json.loads(raw)
                text = parse_chatgpt_export(data) or json.dumps(data, ensure_ascii=False, indent=1)[:8000]
            else:
                text = raw.decode("utf-8", errors="replace")
            chunks.append(f"--- 文件: {f.name} ---\n{text[:6000]}")
        except Exception as e:
            chunks.append(f"--- 文件: {f.name} (读取失败: {e}) ---")
    return "\n\n".join(chunks)

def parse_chatgpt_export(data):
    if not isinstance(data, list):
        return None
    if not data or not isinstance(data[0], dict) or "mapping" not in data[0]:
        return None
    convos = sorted(data, key=lambda c: c.get("update_time", 0) or 0, reverse=True)[:10]
    parts = []
    for c in convos:
        title = c.get("title", "无标题")
        messages = []
        for node in (c.get("mapping") or {}).values():
            msg = (node or {}).get("message")
            if not msg:
                continue
            role = msg.get("author", {}).get("role", "")
            content_parts = msg.get("content", {}).get("parts", [])
            text = " ".join(str(p) for p in content_parts if isinstance(p, str)).strip()
            if text and role in ("user", "assistant"):
                messages.append(f"{'我' if role == 'user' else 'AI'}: {text[:300]}")
        if messages:
            parts.append(f"## {title}\n" + "\n".join(messages[-8:]))
    return "\n\n".join(parts) if parts else None

def scan_folder(folder_path, days=7):
    folder = Path(folder_path).expanduser()
    if not folder.is_dir():
        return None, f"文件夹不存在：{folder}"
    cutoff = datetime.now() - timedelta(days=days)
    files_found = []
    for ext in ["*.txt", "*.md", "*.json", "*.markdown"]:
        for p in folder.rglob(ext):
            if p.stat().st_mtime > cutoff.timestamp():
                files_found.append(p)
    files_found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if not files_found:
        return None, f"最近 {days} 天内没有找到文件"
    chunks = []
    for p in files_found[:20]:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            chunks.append(f"--- {p.name} ---\n{text[:4000]}")
        except Exception:
            pass
    return "\n\n".join(chunks), f"扫描到 {len(chunks)} 个文件"

def fetch_url_text(url):
    """Try to fetch URL content. Returns (text, error)."""
    if not req_lib:
        return None, "需要安装 requests：pip install requests"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        r = req_lib.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:8000], None
    except Exception as e:
        return None, str(e)

# ================================================================
# DATABASE
# ================================================================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pieces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT, module TEXT, idea TEXT,
            hook TEXT, hook_type TEXT,
            title TEXT, cover TEXT, script TEXT, cta TEXT,
            storyboard TEXT, template_used TEXT,
            completion REAL, saves INTEGER, followers INTEGER, why TEXT
        )""")
        for col in ["storyboard", "template_used"]:
            try: conn.execute(f"ALTER TABLE pieces ADD COLUMN {col} TEXT")
            except: pass

        conn.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT, source_label TEXT, raw_text TEXT,
            topic TEXT, pain TEXT, conflict TEXT,
            module TEXT, priority TEXT, reason TEXT,
            status TEXT DEFAULT 'new'
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT, source_url TEXT, source_platform TEXT,
            template_name TEXT, hook_type TEXT,
            structure TEXT, rhythm TEXT, style TEXT,
            why_it_works TEXT, good_for TEXT,
            original_hook TEXT, full_breakdown TEXT,
            original_text TEXT
        )""")

def _next_content_id() -> str:
    """Generate next content_id in CNT-YYYY-NNN format.
    Derived from content_id column — never from artifact_id.
    """
    import datetime
    year = datetime.date.today().year
    with get_db() as conn:
        row = conn.execute(
            "SELECT content_id FROM content_artifacts "
            "WHERE content_id LIKE ? "
            "ORDER BY content_id DESC LIMIT 1",
            (f"CNT-{year}-%",)
        ).fetchone()
    if row:
        last_seq = int(row["content_id"].split("-")[2])
        seq = last_seq + 1
    else:
        seq = 1
    return f"CNT-{year}-{seq:03d}"


def _platform_code(platform: str) -> str:
    mapping = {"xiaohongshu": "XHS", "instagram": "IG"}
    if platform not in mapping:
        raise ValueError(f"Unknown platform '{platform}'. Add it to constants.PLATFORMS and _platform_code().")
    return mapping[platform]


def insert_artifact(a: dict) -> str:
    """
    Insert a content artifact. Generates content_id and artifact_id.
    Returns the artifact_id.
    a must contain all Required fields from Schema v1.0:
      platform, format, topic_type, structure, hook_pattern, hook_text
    Optional: secondary_topics, length, cta, series, language, publish_time, notes
    """
    content_id = _next_content_id()
    platform_code = _platform_code(a["platform"])
    artifact_id = f"{content_id}-{platform_code}-01"

    with get_db() as conn:
        conn.execute(
            """INSERT INTO content_artifacts (
                artifact_id, content_id, platform, format,
                topic_type, structure, hook_pattern, hook_text,
                secondary_topics, length, cta, series,
                language, publish_time, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                artifact_id, content_id,
                a["platform"], a["format"],
                a["topic_type"], a["structure"],
                a["hook_pattern"], a["hook_text"],
                a.get("secondary_topics"),
                a.get("length"),
                a.get("cta"),
                a.get("series"),
                a.get("language", "zh"),
                a.get("publish_time"),
                a.get("notes"),
            )
        )
    return artifact_id


def fetch_artifacts():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM v_artifact_summary ORDER BY publish_time DESC NULLS LAST, artifact_id DESC"
        ).fetchall()


# LEGACY (to be removed in Commit C)
def insert_piece(p):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO pieces (created,module,idea,hook,hook_type,title,cover,script,cta,storyboard,template_used) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (date.today().isoformat(), p["module"], p["idea"],
             p["hook"], p["hook_type"], p["title"], p["cover"],
             p["script"], p["cta"], p.get("storyboard",""), p.get("template_used","")),
        )

def update_stats(pid, completion, saves, followers, why):
    with get_db() as conn:
        conn.execute("UPDATE pieces SET completion=?,saves=?,followers=?,why=? WHERE id=?",
                     (completion, saves, followers, why, pid))

def delete_piece(pid):
    with get_db() as conn:
        conn.execute("DELETE FROM pieces WHERE id=?", (pid,))

def fetch_pieces(order):
    col = "saves" if order == "收藏数" else "completion"
    with get_db() as conn:
        return conn.execute(
            f"SELECT * FROM pieces ORDER BY ({col} IS NULL), {col} DESC, id DESC"
        ).fetchall()

def insert_signal(sig, source_label, raw_text, velocity=None):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO signals (created,source_label,raw_text,topic,pain,conflict,module,priority,reason,velocity) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (date.today().isoformat(), source_label, raw_text,
             sig["topic"], sig["pain"], sig["conflict"],
             sig["module"], sig["priority"], sig["reason"], velocity))

def fetch_signals():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM signals ORDER BY "
            "CASE priority WHEN '高' THEN 0 WHEN '中' THEN 1 ELSE 2 END, id DESC"
        ).fetchall()

def update_signal_status(sid, status):
    with get_db() as conn:
        conn.execute("UPDATE signals SET status=? WHERE id=?", (status, sid))

def delete_signal(sid):
    with get_db() as conn:
        conn.execute("DELETE FROM signals WHERE id=?", (sid,))

def insert_template(t, source_url, platform, original_text):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO templates (created,source_url,source_platform,template_name,"
            "hook_type,structure,rhythm,style,why_it_works,good_for,original_hook,"
            "full_breakdown,original_text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (date.today().isoformat(), source_url, platform,
             t["template_name"], t["hook_type"], t["structure"],
             t["rhythm"], t["style"], t["why_it_works"],
             t["good_for"], t["original_hook"], t["full_breakdown"],
             original_text[:2000]))

def fetch_templates():
    with get_db() as conn:
        return conn.execute("SELECT * FROM templates ORDER BY id DESC").fetchall()

def delete_template(tid):
    with get_db() as conn:
        conn.execute("DELETE FROM templates WHERE id=?", (tid,))

# ================================================================
# CLAUDE
# ================================================================
def get_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        st.error("没找到 ANTHROPIC_API_KEY。先设置再重启。")
        st.stop()
    return Anthropic(api_key=key)

def call_claude(system, user, max_tokens=4000):
    msg = get_client().messages.create(
        model=MODEL, max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")

# ================================================================
# PARSING
# ================================================================
def strip_fences(t):
    return re.sub(r"```json|```", "", t).strip()

def norm_hooks(arr):
    out = []
    for h in arr:
        if not isinstance(h, dict): continue
        hook = (h.get("hook") or h.get("text") or h.get("h") or "").strip()
        typ  = (h.get("type") or h.get("t") or "").strip()
        if hook: out.append({"hook": hook, "type": typ})
    return out

def extract_hooks(text):
    t = strip_fences(text)
    i = t.find("[")
    if i >= 0:
        try:
            arr = json.loads(t[i:])
            if isinstance(arr, list):
                hooks = norm_hooks(arr)
                if hooks: return hooks
        except: pass
    objs = re.findall(r"\{[^{}]*\}", t)
    salvaged = []
    for o in objs:
        try: salvaged.append(json.loads(o))
        except: pass
    hooks = norm_hooks(salvaged)
    if hooks: return hooks
    lines = []
    for line in t.splitlines():
        l = re.sub(r'^\s*[\d\-\.、)）"\'""]+\s*', "", line).strip().strip('"\'""')
        if len(l) > 6 and not re.match(r"^[\[\]{}]", l):
            lines.append(l)
    return [{"hook": l, "type": ""} for l in lines[:8]]

def extract_script(text):
    def field(key):
        m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        return m.group(1).strip() if m else ""
    m = re.search(r"^SCRIPT:\s*\n([\s\S]+)", text, re.MULTILINE | re.IGNORECASE)
    script = m.group(1).strip() if m else text.strip()
    return {"title": field("TITLE"), "cover": field("COVER"), "cta": field("CTA"), "script": script}

def extract_signals(text):
    blocks = re.split(r"===\s*信号\s*\d+\s*===", text)
    signals = []
    for block in blocks:
        block = block.strip()
        if not block: continue
        def grab(key):
            m = re.search(rf"^{key}:\s*(.+)$", block, re.MULTILINE)
            return m.group(1).strip() if m else ""
        topic = grab("选题")
        if not topic: continue
        signals.append({"topic": topic, "pain": grab("痛点"), "conflict": grab("冲突"),
                        "module": grab("模块"), "priority": grab("优先级"), "reason": grab("理由"),
                        "structure": grab("结构")})
    return signals

def extract_template(text):
    def field(key):
        m = re.search(rf"^{key}:\s*(.+?)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""
    m = re.search(r"^FULL_BREAKDOWN:\s*\n?([\s\S]+)", text, re.MULTILINE)
    breakdown = m.group(1).strip() if m else field("FULL_BREAKDOWN")
    return {
        "template_name": field("TEMPLATE_NAME"),
        "hook_type": field("HOOK_TYPE"),
        "structure": field("STRUCTURE"),
        "rhythm": field("RHYTHM"),
        "style": field("STYLE"),
        "why_it_works": field("WHY_IT_WORKS"),
        "good_for": field("GOOD_FOR"),
        "original_hook": field("ORIGINAL_HOOK"),
        "full_breakdown": breakdown,
    }

def extract_recommendations(text):
    blocks = re.split(r"===\s*推荐\s*\d+\s*===", text)
    recs = []
    for block in blocks:
        block = block.strip()
        if not block: continue
        def grab(key):
            m = re.search(rf"^{key}:\s*(.+)$", block, re.MULTILINE)
            return m.group(1).strip() if m else ""
        name = grab("模版")
        if not name: continue
        recs.append({"name": name, "match": grab("匹配度"), "reason": grab("理由"), "adapt": grab("改编建议")})
    return recs

# ================================================================
# SESSION STATE
# ================================================================
def ss():
    s = st.session_state
    for k, v in {"stage": 1, "idea": "", "module": MODULES[0], "hooks": [],
                 "sel": 0, "script": None, "storyboard": "", "sig_raw": "",
                 "sig_source": "", "sig_results": [], "chosen_template": "",
                 "tmpl_text": "", "tmpl_results": None, "recs": [],
                 # Artifact being built through the pipeline
                 "artifact": {
                     "topic_type": TOPIC_TYPES[0],
                     "platform": PLATFORMS[0],
                     "format": "video_short",
                     "structure": "process",
                     "hook_pattern": None,
                     "hook_text": "",
                 }}.items():
        s.setdefault(k, v)
    return s

# ================================================================
# APP
# ================================================================
st.set_page_config(page_title="内容流水线", page_icon="◆", layout="centered")
init_db()
s = ss()

st.markdown(
    "<div style='font-family:monospace;letter-spacing:.2em;color:#E8B14C;font-size:12px'>CONTENT PIPELINE v3</div>"
    "<h2 style='margin:.1em 0 0'>内容流水线</h2>"
    "<div style='color:#888;font-size:13px;margin-bottom:6px'>"
    f"信号 → 模版 → Hook → 脚本 → 分镜 → 入库 · {MODEL}</div>",
    unsafe_allow_html=True,
)

tab_sig, tab_tmpl, tab_pipe, tab_mem = st.tabs(["信号收集", "模版库", "流水线", "记忆库"])

# ===== SIGNAL COLLECTOR =====
with tab_sig:
    st.caption("拖文件、扫文件夹、或手动粘贴。Agent 从里面挖信号。")
    input_mode = st.radio("输入方式", ["📁 拖文件", "📂 扫描文件夹", "📝 手动粘贴"], horizontal=True)

    collected_text = ""
    source_label   = ""

    if input_mode == "📁 拖文件":
        uploaded = st.file_uploader("拖文件", type=["txt","md","json","markdown"], accept_multiple_files=True)
        if uploaded:
            collected_text = read_uploaded_files(uploaded)
            source_label = f"文件上传 ({len(uploaded)})"
            with st.expander(f"预览（{len(collected_text)} 字）"):
                st.text(collected_text[:3000])
    elif input_mode == "📂 扫描文件夹":
        fc, dc = st.columns([3,1])
        fp = fc.text_input("文件夹路径", placeholder="~/Documents/notes")
        sd = dc.number_input("天数", value=7, min_value=1, max_value=90)
        if fp and st.button("扫描"):
            text, msg = scan_folder(fp, int(sd))
            if text:
                collected_text = text; s.sig_raw = text; source_label = f"文件夹: {fp}"
                st.success(msg)
            else: st.warning(msg)
        if not collected_text and s.sig_raw:
            collected_text = s.sig_raw; source_label = "文件夹扫描"
    else:
        SRC = ["ChatGPT / Claude 对话","运营问题 / 数据异常","评论区","竞品内容","卖家群","日记","其他"]
        source_label = st.selectbox("来源", SRC)
        s.sig_raw = st.text_area("原始素材", value=s.sig_raw, height=200, placeholder="粘贴内容…")
        collected_text = s.sig_raw

    if st.button("提取内容信号", type="primary", key="sig_extract"):
        if not collected_text.strip(): st.warning("没有素材。")
        else:
            with st.spinner("提取中…"):
                try:
                    out = call_claude(SIGNAL_SYS, f"素材来源：{source_label}\n\n{collected_text[:10000]}")
                    s.sig_results = extract_signals(out)
                    if not s.sig_results: st.warning("没提取到信号。")
                except Exception as e: st.error(f"失败：{e}")

    if s.sig_results:
        st.markdown("---")
        for i, sig in enumerate(s.sig_results):
            with st.container(border=True):
                pri = {"高":"🔴","中":"🟡","低":"⚪"}.get(sig["priority"],"⚪")
                st.markdown(f"{pri} **{sig['topic']}**")
                st.caption(f"`{sig['module']}` · {sig['priority']}")
                if sig["conflict"]: st.caption(f"冲突：{sig['conflict']}")
                if sig.get("structure"): st.caption(f"结构：{sig['structure']}")
                c1,c2 = st.columns(2)
                vel = c1.selectbox("时机", ["rising 🚀","plateau ➡️","saturated 💀"],
                    key=f"vel{i}", label_visibility="collapsed")
                vel_val = vel.split(" ")[0]
                if c1.button("存入信号库", key=f"ss{i}"):
                    insert_signal(sig, source_label, collected_text[:500], velocity=vel_val); st.success("已存")
                if c2.button("做内容 →", key=f"su{i}"):
                    s.idea = sig["topic"]
                    for m in MODULES:
                        if m[:3] in sig.get("module",""): s.module = m; break
                    s.hooks=[]; s.script=None; s.storyboard=""; st.success("切到「流水线」tab")

    st.markdown("---")
    st.caption("信号库")
    for r in fetch_signals():
        with st.container(border=True):
            pri = {"高":"🔴","中":"🟡","低":"⚪"}.get(r["priority"],"⚪")
            tag = " · ✅" if r["status"]=="used" else ""
            vel_icon = {"rising":"🚀","plateau":"➡️","saturated":"💀"}.get(r["velocity"] or "","")
            st.markdown(f"{pri} **{r['topic']}**{tag} {vel_icon}")
            st.caption(f"`{r['module']}` · {r['created']}")
            c1,c2,c3 = st.columns(3)
            if c1.button("做内容→", key=f"sbu{r['id']}"):
                s.idea=r["topic"]; update_signal_status(r["id"],"used"); st.success("切到流水线")
            if c2.button("已用", key=f"sm{r['id']}"): update_signal_status(r["id"],"used"); st.rerun()
            if c3.button("删", key=f"sd{r['id']}"): delete_signal(r["id"]); st.rerun()

# ===== TEMPLATE LIBRARY =====
with tab_tmpl:
    st.caption("粘贴一条爆款内容的链接或文案，Agent 拆解结构存入模版库。流水线写脚本时会推荐最匹配的模版。")

    tmpl_input = st.radio("输入方式", ["🔗 链接", "📝 粘贴文案"], horizontal=True)

    tmpl_url = ""
    tmpl_platform = ""

    if tmpl_input == "🔗 链接":
        tmpl_url = st.text_input("链接", placeholder="https://www.instagram.com/reel/... 或小红书链接")
        TMPL_PLATFORMS = ["Instagram", "小红书", "TikTok", "YouTube", "其他"]
        tmpl_platform = st.selectbox("平台", TMPL_PLATFORMS)
        st.caption("⚠️ 社交媒体链接经常需要登录才能抓取。如果抓取失败，下面可以补贴文案内容。")
    else:
        TMPL_PLATFORMS = ["Instagram", "小红书", "TikTok", "YouTube", "其他"]
        tmpl_platform = st.selectbox("平台", TMPL_PLATFORMS, key="tp2")

    s.tmpl_text = st.text_area(
        "文案内容（视频口播稿 / 帖子正文 / caption）",
        value=s.tmpl_text, height=200,
        placeholder="把视频的口播稿或者帖子正文粘贴到这里。如果是视频，可以用字幕提取工具先拿到文字。",
    )

    if st.button("分析内容结构", type="primary", key="tmpl_analyze"):
        content = s.tmpl_text.strip()

        if tmpl_url.strip() and not content:
            with st.spinner("尝试抓取链接…"):
                fetched, err = fetch_url_text(tmpl_url.strip())
                if fetched:
                    content = fetched
                    st.success("抓取成功")
                else:
                    st.warning(f"抓取失败（{err}）。请手动粘贴文案内容。")

        if not content:
            st.warning("需要文案内容才能分析。粘贴口播稿/正文到上面的文本框。")
        else:
            with st.spinner("拆解内容结构中…"):
                try:
                    out = call_claude(
                        TEMPLATE_ANALYZE_SYS,
                        f"平台：{tmpl_platform}\n来源：{tmpl_url or '手动粘贴'}\n\n内容原文：\n{content[:6000]}",
                    )
                    s.tmpl_results = extract_template(out)
                    if not s.tmpl_results.get("template_name"):
                        st.warning("没有提取到有效模版，再试一次。")
                        s.tmpl_results = None
                except Exception as e:
                    st.error(f"分析失败：{e}")

    if s.tmpl_results:
        st.markdown("---")
        t = s.tmpl_results
        st.markdown(f"### 📐 {t['template_name']}")
        st.caption(f"Hook 类型：{t['hook_type']}")
        st.markdown(f"**结构：** {t['structure']}")
        if t["rhythm"]: st.caption(f"节奏：{t['rhythm']}")
        if t["style"]: st.caption(f"风格：{t['style']}")
        if t["why_it_works"]: st.caption(f"为什么有效：{t['why_it_works']}")
        if t["good_for"]: st.caption(f"适合选题：{t['good_for']}")
        if t["original_hook"]: st.caption(f"原 Hook：{t['original_hook']}")
        if t["full_breakdown"]:
            with st.expander("逐段拆解"):
                st.text(t["full_breakdown"])

        if st.button("存入模版库", type="primary", key="tmpl_save"):
            insert_template(t, tmpl_url, tmpl_platform, s.tmpl_text[:2000])
            st.success(f"模版「{t['template_name']}」已存入。")
            s.tmpl_results = None
            s.tmpl_text = ""

    st.markdown("---")
    st.caption("模版库")
    all_tmpls = fetch_templates()
    if not all_tmpls:
        st.info("模版库还是空的。分析几条爆款内容，把它们的结构存进来。")
    else:
        for t in all_tmpls:
            with st.container(border=True):
                st.markdown(f"**📐 {t['template_name']}** · `{t['source_platform']}`")
                st.caption(f"结构：{t['structure']}")
                st.caption(f"适合：{t['good_for']}")
                st.caption(f"Hook：{t['hook_type']} · {t['created']}")
                c1, c2 = st.columns([1,1])
                if c1.button("看详情", key=f"td{t['id']}"):
                    with st.expander("完整拆解", expanded=True):
                        st.text(t["full_breakdown"])
                if c2.button("删除", key=f"tdd{t['id']}"):
                    delete_template(t["id"]); st.rerun()

# ===== PIPELINE =====
with tab_pipe:
    s.idea = st.text_area("选题", value=s.idea, height=100,
        placeholder="一个想法、一个运营问题、或从信号库推过来的选题")
    s.module = st.radio("模块", MODULES, horizontal=True, index=MODULES.index(s.module))

    # ── Intent Metadata (Layer 1) ──────────────────────────────────────────
    # Captured at start of pipeline — these are known before writing begins.
    with st.expander("Intent Metadata", expanded=True):
        ic1, ic2, ic3 = st.columns(3)
        s.artifact["topic_type"] = ic1.selectbox(
            "Topic Type",
            TOPIC_TYPES,
            index=TOPIC_TYPES.index(s.artifact.get("topic_type", TOPIC_TYPES[0])),
        )
        s.artifact["platform"] = ic2.selectbox(
            "Platform",
            PLATFORMS,
            index=PLATFORMS.index(s.artifact.get("platform", PLATFORMS[0])),
        )
        s.artifact["format"] = ic3.selectbox(
            "Format",
            FORMATS,
            index=FORMATS.index(s.artifact.get("format", "video_short")),
        )
    # ── End Intent Metadata ────────────────────────────────────────────────

    if st.button("① 生成 Hook", type="primary"):
        if not s.idea.strip(): st.warning("先写选题。")
        else:
            with st.spinner("生成 hook…"):
                try:
                    out = call_claude(HOOK_SYS,
                        f'生成 6 个 hook。JSON 数组：[{{"hook":"...","type":"<schema_enum>"}}]。'
                        f'type 必须输出 Schema enum 值（见 Prompt 定义）。每个 hook ≤35 字。\n\n内容：{s.idea}\n模块：{s.module}')
                    s.hooks = extract_hooks(out); s.sel=0; s.script=None; s.storyboard=""; s.recs=[]
                    s.chosen_template = ""
                    if not s.hooks:
                        st.error("没解析出 hook。")
                    else:
                        from pipeline.hook_scorer import score_hook
                        scored = []
                        for h in s.hooks:
                            result = score_hook(h["hook"])
                            h["score"] = result["total"]
                            h["passed"] = result["passed"]
                            h["rationale"] = result["rationale"]
                            scored.append(h)
                        s.hooks = scored
                        # Update artifact with hook data from selected hook (index 0 initially)
                        # Will be refreshed when user selects a different hook
                        if scored:
                            best = scored[0]
                            s.artifact["hook_text"] = best["hook"]
                            s.artifact["hook_pattern"] = (
                                best["type"] if best.get("type") in HOOK_PATTERNS else None
                            )
                except Exception as e: st.error(f"失败：{e}")

    if s.hooks:
        st.markdown("---")
        st.caption("② 选 hook")
        labels = [
            f"{'✅' if h.get('passed') else '❌'} [{h['type'] or 'hook'}] {h['hook']} (分:{h.get('score','?')})"
            for h in s.hooks
        ]
        s.sel = st.radio("hook", range(len(labels)), format_func=lambda i: labels[i], label_visibility="collapsed")
        if s.hooks and s.sel < len(s.hooks):
            h = s.hooks[s.sel]
            if h.get("rationale"):
                st.caption(f"💡 {h['rationale']}")
            # Keep artifact in sync with selected hook
            s.artifact["hook_text"] = h["hook"]
            s.artifact["hook_pattern"] = (
                h.get("type") if h.get("type") in HOOK_PATTERNS else None
            )

        all_tmpls = fetch_templates()
        if all_tmpls:
            if st.button("推荐匹配模版", key="rec_tmpl"):
                with st.spinner("匹配中…"):
                    try:
                        tmpl_summary = "\n".join([
                            f"- {t['template_name']}：结构={t['structure']}，适合={t['good_for']}，hook类型={t['hook_type']}"
                            for t in all_tmpls
                        ])
                        out = call_claude(TEMPLATE_RECOMMEND_SYS,
                            f"选题：{s.idea}\nHook：{s.hooks[s.sel]['hook']}\n\n模版库：\n{tmpl_summary}")
                        s.recs = extract_recommendations(out)
                        if not s.recs: st.info("没有高匹配的模版，自由发挥。")
                    except Exception as e: st.error(f"推荐失败：{e}")

            if s.recs:
                for i, rec in enumerate(s.recs):
                    with st.container(border=True):
                        match_color = "🟢" if rec["match"] == "高" else "🟡"
                        st.markdown(f"{match_color} **{rec['name']}** · 匹配度：{rec['match']}")
                        st.caption(f"理由：{rec['reason']}")
                        if rec["adapt"]: st.caption(f"改编建议：{rec['adapt']}")
                        if st.button(f"用这个模版", key=f"usetmpl{i}"):
                            for t in all_tmpls:
                                if t["template_name"] in rec["name"] or rec["name"] in t["template_name"]:
                                    s.chosen_template = (
                                        f"模版名：{t['template_name']}\n"
                                        f"结构：{t['structure']}\n"
                                        f"节奏：{t['rhythm']}\n"
                                        f"风格：{t['style']}\n"
                                        f"拆解：{t['full_breakdown'][:800]}"
                                    )
                                    break
                            st.success(f"已选模版：{rec['name']}")

        if s.chosen_template:
            st.caption(f"✅ 当前参考模版已选定")
            if st.button("取消模版", key="cleartmpl"):
                s.chosen_template = ""; st.rerun()

        if st.button("② 写脚本", type="primary"):
            with st.spinner("写脚本…"):
                try:
                    hk = s.hooks[s.sel]["hook"]
                    user_msg = f"选定 Hook：{hk}\n选题：{s.idea}\n模块：{s.module}"
                    if s.chosen_template:
                        user_msg += f"\n\n参考模版（模仿结构，不要照搬用词）：\n{s.chosen_template}"
                    out = call_claude(SCRIPT_SYS, user_msg)
                    s.script = extract_script(out); s.storyboard=""
                    if not s.script["script"]: st.error("脚本为空。")
                except Exception as e: st.error(f"失败：{e}")

    if s.script and s.script.get("script"):
        st.markdown("---")
        st.caption("③ 脚本")
        title  = st.text_input("标题", value=s.script["title"])
        cover  = st.text_input("封面", value=s.script["cover"])
        script = st.text_area("口播稿", value=s.script["script"], height=320)
        cta    = st.text_input("CTA", value=s.script["cta"])
        s.script.update({"title": title, "cover": cover, "script": script, "cta": cta})

        if st.button("③ 生成分镜", type="primary"):
            with st.spinner("分镜…"):
                try:
                    out = call_claude(VISUAL_SYS, f"标题：{title}\n口播稿：\n{script}")
                    s.storyboard = strip_fences(out)
                except Exception as e: st.error(f"失败：{e}")

    if s.storyboard:
        st.markdown("---")
        st.caption("④ 分镜")
        storyboard = st.text_area("分镜方案", value=s.storyboard, height=420)
        s.storyboard = storyboard
        st.markdown("---")

        # ── Artifact Review (Layer 2) ──────────────────────────────────────
        # Metadata confirmed after creation. Auto-populated from pipeline;
        # user confirms structure and resolves any missing hook_pattern.
        st.caption("④ Artifact Review")
        with st.container(border=True):
            rc1, rc2 = st.columns(2)

            # Structure: default to "process"; user confirms.
            # Evidence-based recommendation deferred to Commit C.
            current_structure = s.artifact.get("structure", "process")
            if current_structure not in STRUCTURES:
                current_structure = "process"
            s.artifact["structure"] = rc1.selectbox(
                "Structure",
                STRUCTURES,
                index=STRUCTURES.index(current_structure),
            )

            # hook_pattern: auto from hook type, fallback to selectbox
            current_pattern = s.artifact.get("hook_pattern")
            pattern_valid = current_pattern in HOOK_PATTERNS
            if pattern_valid:
                rc2.markdown(f"**Hook Pattern**")
                rc2.code(current_pattern)
            else:
                # Anomaly path: model returned invalid type, require manual selection
                st.warning("Hook pattern 未自动识别，请手动选择后才能保存。")
                s.artifact["hook_pattern"] = rc2.selectbox(
                    "Hook Pattern ⚠️",
                    HOOK_PATTERNS,
                )
                pattern_valid = True

            # Read-only confirmation fields
            st.caption(f"**Topic Type:** `{s.artifact.get('topic_type')}` · "
                      f"**Platform:** `{s.artifact.get('platform')}` · "
                      f"**Format:** `{s.artifact.get('format')}`")
            st.caption(f"**Hook:** {s.artifact.get('hook_text', '')}")

            # Save — blocked if hook_pattern still invalid
            can_save = pattern_valid and bool(s.artifact.get("hook_text", "").strip())
            if st.button("④ 创建 Artifact", type="primary", disabled=not can_save):
                artifact_id = insert_artifact(s.artifact)
                st.success(f"Artifact 已创建：`{artifact_id}`。去拍。发完回来填 Performance。")
                # Reset pipeline state
                s.stage=1; s.idea=""; s.hooks=[]; s.script=None; s.storyboard=""
                s.chosen_template=""; s.recs=[]
                s.artifact = {
                    "topic_type": TOPIC_TYPES[0],
                    "platform": PLATFORMS[0],
                    "format": "video_short",
                    "structure": "process",
                    "hook_pattern": None,
                    "hook_text": "",
                }
        # ── End Artifact Review ────────────────────────────────────────────

# ===== MEMORY =====
with tab_mem:
    order = st.selectbox("排序", ["收藏数", "完播率"])
    rows = fetch_pieces(order)
    if not rows:
        st.info("记忆库空的。做完→发→回来填数据。")
    else:
        for r in rows:
            with st.container(border=True):
                c1,c2 = st.columns([5,1])
                c1.markdown(f"**{r['title']}**"); c2.caption(r["created"])
                st.caption(f"`{r['module']}` · [{r['hook_type'] or ''}] {r['hook']}")
                if r["completion"] is not None or r["saves"] is not None or r["followers"] is not None:
                    m1,m2,m3 = st.columns(3)
                    m1.metric("完播率", f"{r['completion']}%" if r["completion"] is not None else "—")
                    m2.metric("收藏", r["saves"] if r["saves"] is not None else "—")
                    m3.metric("涨粉", r["followers"] if r["followers"] is not None else "—")
                    if r["why"]: st.caption(f"为什么：{r['why']}")
                with st.expander("回填数据"):
                    f1,f2,f3 = st.columns(3)
                    comp = f1.number_input("完播率%", value=float(r["completion"] or 0), step=0.1, key=f"c{r['id']}")
                    sav  = f2.number_input("收藏", value=int(r["saves"] or 0), step=1, key=f"s{r['id']}")
                    fol  = f3.number_input("涨粉", value=int(r["followers"] or 0), step=1, key=f"f{r['id']}")
                    why  = st.text_area("这条证明了什么", value=r["why"] or "", key=f"w{r['id']}", height=70)
                    b1,b2 = st.columns(2)
                    if b1.button("保存", key=f"sv{r['id']}"): update_stats(r["id"],comp,int(sav),int(fol),why.strip()); st.rerun()
                    if b2.button("删除", key=f"dl{r['id']}"): delete_piece(r["id"]); st.rerun()
                with st.expander("脚本"): st.text(r["script"])
                sb = r["storyboard"] if "storyboard" in r.keys() else ""
                if sb:
                    with st.expander("分镜"): st.text(sb)
