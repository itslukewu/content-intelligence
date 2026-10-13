"""Topic Library v1.2 — SQLite helpers, Python standard library only."""
import argparse
import json
import re
import sqlite3
import uuid
from pathlib import Path

from pipeline.settings import DB_PATH

ROOT = Path(__file__).resolve().parent
QUALITY = ('audience_relevance','information_gain','evidence_quality','clarity','share_motivation','narrative_tension','account_fit')
PRIORITY = ('demand','business_value','feasibility')
STATES = ('idea','pending_review','approved','scheduled','in_production','qa','published','reviewed','paused')
ALLOWED = {
 'idea': {'pending_review','paused'},
 'pending_review': {'approved','idea','paused'},
 'approved': {'scheduled','in_production','paused'},
 'scheduled': {'in_production','paused'},
 'in_production': {'qa','paused'},
 'qa': {'published','in_production','paused'},
 'published': {'reviewed'},
 'reviewed': set(),
 'paused': {'idea','pending_review'}
}
BRIEF_FIELDS = ('audience','pain_point','core_insight','hook','evidence','target_action','score_reasoning')
AI_REQUIRED = BRIEF_FIELDS + ('quality_scores','priority_scores')

def connect(path):
    db=sqlite3.connect(path)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def _columns(db, table):
    return {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}

def _table_exists(db, table):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _add_column(db, table, name, ddl):
    if _table_exists(db, table) and name not in _columns(db, table):
        db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')

def init(db):
    base=ROOT.parent / 'specs' / 'schema_v1.0.sql'
    if base.exists():
        db.executescript(base.read_text())
    db.execute("""CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created TEXT, source_label TEXT, raw_text TEXT,
        topic TEXT, pain TEXT, conflict TEXT,
        module TEXT, priority TEXT, reason TEXT,
        status TEXT DEFAULT 'new',
        velocity TEXT
    )""")
    db.executescript((ROOT.parent / 'specs' / 'topic_library_v1.sql').read_text())
    _add_column(db, 'topics', 'score_reasoning', 'TEXT')
    _add_column(db, 'signals', 'velocity', 'TEXT')
    db.execute('CREATE INDEX IF NOT EXISTS idx_topics_source_reference ON topics(source_reference)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_topic_status_history ON topic_status_history(topic_id, changed_at)')
    db.commit()

def create(db,title,account='Unassigned',series=None,source_reference=None):
    tid='T-'+uuid.uuid4().hex[:12].upper()
    db.execute('INSERT INTO topics(topic_id,title,account,series,source_reference) VALUES(?,?,?,?,?)',
               (tid,title,account,series,source_reference))
    db.commit()
    return tid

def score(db,tid,values):
    if set(values)!=set(QUALITY+PRIORITY):
        raise ValueError('Provide exactly 7 quality and 3 priority dimensions')
    if any(type(values[k]) is not int or not 0<=values[k]<=5 for k in QUALITY):
        raise ValueError('Quality dimensions must be integers 0–5')
    if any(type(values[k]) is not int or not 1<=values[k]<=3 for k in PRIORITY):
        raise ValueError('Priority dimensions must be integers 1–3')
    q=sum(values[k] for k in QUALITY)
    p=sum(values[k] for k in PRIORITY)
    tier='P0' if p>=8 else 'P1' if p>=6 else 'P2'
    # Gate is advisory, not automatic approval.
    gate='revise' if q<23 or values['information_gain']<3 or values['evidence_quality']<3 else 'eligible'
    fields=QUALITY+PRIORITY
    with db:
        db.execute('INSERT INTO topic_scores(topic_id,'+','.join(fields)+') VALUES ('+','.join('?' for _ in range(11))+') ON CONFLICT(topic_id) DO UPDATE SET '+','.join(f'{f}=excluded.{f}' for f in fields)+",scored_at=datetime('now')",[tid]+[values[k] for k in fields])
        db.execute("UPDATE topics SET insight_score=?,priority_score=?,priority=?,updated_at=datetime('now') WHERE topic_id=?",(q,p,tier,tid))
    return {'quality':q,'priority_score':p,'priority':tier,'quality_gate':gate}

def _strip_code_fence(value):
    value=value.strip()
    match=re.fullmatch(r"```(?:json|JSON)?\s*(.*?)\s*```", value, flags=re.DOTALL)
    return match.group(1).strip() if match else value

def parse_ai_json(value):
    return json.loads(_strip_code_fence(value))

def validate_ai_brief(obj):
    if not isinstance(obj, dict):
        raise ValueError('AI response must be a JSON object')
    missing=[k for k in AI_REQUIRED if k not in obj]
    if missing:
        raise ValueError('AI response missing fields: '+', '.join(missing))
    normalized={}
    for k in BRIEF_FIELDS:
        if obj[k] is None:
            normalized[k]=''
        elif isinstance(obj[k], (str, int, float, bool)):
            normalized[k]=str(obj[k]).strip()
        else:
            raise ValueError(f'AI field {k} must be text')
    q=obj['quality_scores']
    p=obj['priority_scores']
    if not isinstance(q, dict) or not isinstance(p, dict):
        raise ValueError('AI scores must be JSON objects')
    values={}
    for k in QUALITY:
        if k not in q or type(q[k]) is not int or not 0 <= q[k] <= 5:
            raise ValueError(f'Invalid quality score: {k}')
        values[k]=q[k]
    for k in PRIORITY:
        if k not in p or type(p[k]) is not int or not 1 <= p[k] <= 3:
            raise ValueError(f'Invalid priority score: {k}')
        values[k]=p[k]
    normalized['quality_scores']={k:values[k] for k in QUALITY}
    normalized['priority_scores']={k:values[k] for k in PRIORITY}
    return normalized, values

def generate_ai_brief(ai_call, system_prompt, request, repair_prompt=None):
    raw=ai_call(system_prompt, request)
    responses=[raw]
    try:
        obj=parse_ai_json(raw)
        normalized, values=validate_ai_brief(obj)
        return normalized, values, responses
    except Exception as first_error:
        if repair_prompt is None:
            repair_prompt='你是 JSON 格式修复器。仅返回一个合法 JSON 对象，不添加或编造内容；保持字段和值原意。'
        retry=ai_call(repair_prompt, '将下面文本转换为合法 JSON；不要使用 Markdown 代码块，不要补充原文没有的信息：\n'+raw[:14000])
        responses.append(retry)
        try:
            obj=parse_ai_json(retry)
            return (*validate_ai_brief(obj), responses)
        except Exception as retry_error:
            raise ValueError(f'AI JSON validation failed after retry: {first_error}; retry failed: {retry_error}') from retry_error

def gate_result(db, tid):
    row=db.execute("SELECT * FROM topic_scores WHERE topic_id=?", (tid,)).fetchone()
    if row is None:
        return {'eligible':False,'reason':'尚未评分'}
    q=sum(row[k] for k in QUALITY)
    problems=[]
    if q<23: problems.append(f'质量 {q}/35，低于 23')
    if row['information_gain']<3: problems.append('信息增量低于 3')
    if row['evidence_quality']<3: problems.append('证据质量低于 3')
    return {'eligible':not problems,'reason':'；'.join(problems) or '符合评分门槛'}


def update_brief(db,tid,fields):
    allowed={'audience','pain_point','core_insight','hook','evidence','source_reference','series','format','platform','target_action','notes','score_reasoning'}
    if not fields or not set(fields)<=allowed: raise ValueError('Unsupported brief fields')
    if not db.execute('SELECT 1 FROM topics WHERE topic_id=?',(tid,)).fetchone(): raise ValueError('Unknown topic')
    with db:
        db.execute('UPDATE topics SET '+','.join(k+'=?' for k in fields)+",updated_at=datetime('now') WHERE topic_id=?",[*fields.values(),tid])


def create_from_signal(db,signal_id):
    signal=db.execute('SELECT * FROM signals WHERE id=?',(signal_id,)).fetchone()
    if signal is None: raise ValueError('Unknown signal')
    source=f'signal:{signal_id}'
    existing=db.execute('SELECT topic_id FROM topics WHERE source_reference=?',(source,)).fetchone()
    if existing: return existing['topic_id'],False
    tid=create(db,signal['topic'],source_reference=source)
    update_brief(db,tid,{'pain_point':signal['pain'] or '', 'evidence':signal['raw_text'] or '', 'notes':signal['conflict'] or ''})
    return tid,True


def transition(db,tid,new_status,pause_reason=None,override_reason=None):
    row=db.execute('SELECT status FROM topics WHERE topic_id=?',(tid,)).fetchone()
    if row is None: raise ValueError('Unknown topic ID')
    if new_status not in ALLOWED[row['status']]: raise ValueError(f"Invalid transition: {row['status']} -> {new_status}")
    if new_status=='paused' and not pause_reason: raise ValueError('Pause reason required')
    if new_status=='approved':
        s=db.execute('SELECT insight_score FROM topics WHERE topic_id=?',(tid,)).fetchone()
        if s['insight_score'] is None: raise ValueError('Score before approval')
        gate=gate_result(db,tid)
        if not gate['eligible'] and not (override_reason and override_reason.strip()):
            raise ValueError('Approval blocked: '+gate['reason']+'；如需人工批准，请填写 Override 原因')
    with db:
        db.execute("UPDATE topics SET status=?,pause_reason=?,updated_at=datetime('now') WHERE topic_id=?",(new_status,pause_reason,tid))
        db.execute("INSERT INTO topic_status_history(topic_id,from_status,to_status,override_reason) VALUES(?,?,?,?)",(tid,row['status'],new_status,override_reason.strip() if override_reason else None))

def link(db,tid,artifact_id):
    if not db.execute('SELECT 1 FROM topics WHERE topic_id=?',(tid,)).fetchone(): raise ValueError('Unknown topic ID')
    if not db.execute('SELECT 1 FROM content_artifacts WHERE artifact_id=?',(artifact_id,)).fetchone():
        raise ValueError('Unknown artifact ID')
    with db: db.execute('INSERT OR IGNORE INTO topic_artifact_links(topic_id,artifact_id) VALUES(?,?)',(tid,artifact_id))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db',default=str(DB_PATH))
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('init')
    a=sub.add_parser('add');a.add_argument('title');a.add_argument('--account',default='Unassigned');a.add_argument('--series');a.add_argument('--source')
    a=sub.add_parser('score');a.add_argument('id');a.add_argument('--json',required=True,help='JSON object with 10 scores')
    a=sub.add_parser('move');a.add_argument('id');a.add_argument('status',choices=STATES);a.add_argument('--reason')
    a=sub.add_parser('link');a.add_argument('id');a.add_argument('artifact_id')
    a=sub.add_parser('list');a.add_argument('--status');a.add_argument('--account')
    args=p.parse_args()
    db=connect(args.db)
    if args.cmd=='init': init(db);print('Initialized additive Topic Library schema')
    elif args.cmd=='add': print(create(db,args.title,args.account,args.series,args.source))
    elif args.cmd=='score': print(json.dumps(score(db,args.id,json.loads(args.json)),ensure_ascii=False))
    elif args.cmd=='move': transition(db,args.id,args.status,args.reason);print('OK')
    elif args.cmd=='link': link(db,args.id,args.artifact_id);print('OK')
    elif args.cmd=='list':
        q='SELECT * FROM topics WHERE 1=1';params=[]
        if args.status:q+=' AND status=?';params.append(args.status)
        if args.account:q+=' AND account=?';params.append(args.account)
        q+=' ORDER BY created_at DESC'
        for row in db.execute(q,params):print(json.dumps(dict(row),ensure_ascii=False))

if __name__=='__main__':main()
