#!/usr/bin/env python3
"""Deterministic analysis layer: creator_intelligence.json -> analysis.json
数字全部来自本脚本;LLM 合成层(Stage 4)只解释,不计算。

Usage:
    python3 audience-analyze.py <creator_intelligence.json> <out_analysis.json>
"""
import json, re, sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# ---- 冻结的主题归并表(可按周维护,新增别名往里加)----
TOPIC_GROUPS = {
    'claude':        ['claude','claudeai','claudecode','anthropic','anthropicai','claudefable','claude5','claudecodesetup','claudeplugins'],
    'ai-agents':     ['aiagent','aiagents','agent','agents','aiautomation','automation','n8n','make'],
    'vibecoding':    ['vibecoding','vibecode','aicoding','cursor','cursorcreator','indiedev','indiedeveloper','coding','buildinpublic'],
    'prompts':       ['prompt','prompts','prompting','promptengineering','systemprompt'],
    'second-brain':  ['secondbrain','notion','obsidian','pkm','notetaking','productivity'],
    'make-money-ai': ['makemoneyonline','makemoney','sidehustle','passiveincome','millionairemindset','entrepreneur','business'],
    'content-social':['socialmediamarketing','contentcreation','contentcreator','socialmedia','instagramgrowth','marketing','shortform'],
    'chatgpt-openai':['chatgpt','openai','gpt','sora','chatgptprompts'],
}
MERGE = {a: c for c, alts in TOPIC_GROUPS.items() for a in alts}
MIN_COUNT = 3
FRAMES = {
    'question':   r"\b(how (do|to|can|i)|why |what('s| is| if)|can (i|you)|should (i|you))\b",
    'resistance': r"\b(everyone (says|thinks)|stop |scam|dangerous|wrong|mistake|myth|don't need|too (hard|complex|late)|replace)\b",
    'aspiration': r"\b(grew|grow|10x|ma(k|d)e \$|million|passive|freedom|one[- ]person|solo|quit|no team|in \d+ (days|weeks|minutes|hours))\b",
    'pain':       r"\b(struggl|can't|cannot|don't know|overwhelm|wast(e|ing)|stuck|confus|fail(ed|ing)?|hardest|problem)\b",
}

def tier(n_creators):
    return 'confirmed' if n_creators >= 3 else ('emerging' if n_creators == 2 else 'weak')

def main(src, dst):
    data = json.load(open(src))
    posts = data['scored_posts']
    now = datetime.now(timezone.utc)
    total_views = sum(p['post'].get('views') or 0 for p in posts) or 1
    rp = lambda p: p['score'].get('relative_performance_multiplier') or 0
    txt = lambda p: ((p['post'].get('title') or '') + ' ' + (p['post'].get('text') or ''))

    # 1) topic clustering + supply gap
    tp = defaultdict(list)
    for p in posts:
        for t in {MERGE.get(t.lower().strip(), t.lower().strip()) for t in (p['post'].get('tags') or [])}:
            tp[t].append(p)
    topics, outliers = [], []
    for t, pl in tp.items():
        row = {'topic': t, 'posts': len(pl),
               'creators': len({q['post']['author'] for q in pl}),
               'frequency_share': round(len(pl)/len(posts), 4),
               'engagement_share': round(sum(q['post'].get('views') or 0 for q in pl)/total_views, 4),
               'avg_rp': round(sum(rp(q) for q in pl)/len(pl), 2)}
        row['supply_gap'] = round(row['engagement_share'] - row['frequency_share'], 4)
        row['evidence_strength'] = tier(row['creators'])
        (topics if len(pl) >= MIN_COUNT else outliers).append(row)
    topics.sort(key=lambda r: -abs(r['supply_gap']))

    # 2) frame extraction (RP>1 only)
    frames = {k: [] for k in FRAMES}
    for p in posts:
        if rp(p) <= 1.0: continue
        body = txt(p)
        for name, pat in FRAMES.items():
            if re.search(pat, body, re.I):
                frames[name].append({'rp': round(rp(p),1), 'author': p['post']['author'],
                                     'title': (p['post'].get('title') or '')[:110],
                                     'url': p['post'].get('url')})
    for k in frames:
        frames[k] = sorted(frames[k], key=lambda x: -x['rp'])[:12]

    # 3) emerging tags (first seen <=14d, views>50k)
    first = {}
    for p in sorted(posts, key=lambda p: p['post'].get('published_at') or ''):
        d = p['post'].get('published_at')
        if not d: continue
        t0 = datetime.fromisoformat(d)
        for tag in (p['post'].get('tags') or []):
            first.setdefault(tag.lower(), (t0, p['post'].get('views') or 0))
    emerging = sorted([{'tag': t, 'first_seen': v[0].date().isoformat(), 'views': v[1]}
                       for t, v in first.items()
                       if (now - v[0]) <= timedelta(days=14) and v[1] > 50000],
                      key=lambda x: -x['views'])[:15]

    out = {
        'generated_at': now.isoformat(),
        'health': {
            'posts': len(posts), 'creators': len({p['post']['author'] for p in posts}),
            'total_views': total_views, 'topic_min_count': MIN_COUNT,
            'topics_before_merge': len(tp), 'topics_after_min_count': len(topics),
            'outlier_topics': len(outliers),
            'followers': 'degraded' if all((p['post'].get('followers') or 0) == 0 for p in posts) else 'ok',
            'provenance': 'post_content',
            'warnings': [w for w in [
                'followers missing — no cross-account normalization' if all((p['post'].get('followers') or 0)==0 for p in posts) else None,
                f'pain frames thin ({len(frames["pain"])})' if len(frames['pain']) < 5 else None,
            ] if w],
        },
        'supply_gap_table': topics[:15],
        'frames': frames,
        'emerging_tags': emerging,
    }
    json.dump(out, open(dst, 'w'), ensure_ascii=False, indent=1)
    print(f"analysis written: {dst} | topics {len(topics)} | warnings {out['health']['warnings']}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
