"""Topic Library v1.1: compact review workbench."""
import json
import streamlit as st
from pipeline.settings import DB_PATH
from pipeline.topic_library import (connect,create,score,transition,QUALITY,PRIORITY,ALLOWED,
                                    gate_result,update_brief,create_from_signal)
LABELS=dict(zip(QUALITY+PRIORITY,['受众相关性','信息增量','证据质量','观点清晰','传播动机','叙事张力','账号匹配','用户需求','业务价值','制作可行性']))

SYSTEM='''你是内容选题编辑。只依据提供的标题、来源和素材，不得编造个人经历、销量、金额或市场数据。输出严格 JSON 对象：audience,pain_point,core_insight,hook,evidence,target_action,score_reasoning,quality_scores,priority_scores。quality_scores 含 audience_relevance,information_gain,evidence_quality,clarity,share_motivation,narrative_tension,account_fit，0到5整数；priority_scores 含 demand,business_value,feasibility，1到3整数。缺乏证据时 evidence 写「待补充」，evidence_quality 不超过2；score_reasoning 简洁说明缺口。避免伪悬念和 AI can X but can it Y 句式。'''

def render(ai_call=None):
    st.subheader('Topic Library · 选题工作台')
    with connect(DB_PATH) as db:
        with st.expander('＋ 新建选题',expanded=False):
            with st.form('topic_add_v11',clear_on_submit=True):
                title=st.text_input('选题标题')
                account=st.selectbox('账号',['Unassigned','Luke 2.0','Amazon x AI'])
                series=st.text_input('Series')
                source=st.text_input('素材来源 / Reference')
                if st.form_submit_button('保存到 Idea Inbox'):
                    if title.strip():
                        tid=create(db,title.strip(),account,series or None,source or None)
                        st.success(f'已保存 {tid}')
                        st.rerun()
                    else: st.warning('请输入标题')
        with st.expander('从信号库导入',expanded=False):
            try:
                signals=db.execute('SELECT id,topic FROM signals ORDER BY id DESC LIMIT 100').fetchall()
                if signals:
                    sig=st.selectbox('已有信号',signals,format_func=lambda r:f"#{r['id']} · {r['topic']}")
                    if st.button('导入 Idea Inbox'):
                        tid,created=create_from_signal(db,sig['id'])
                        st.success(f"{'已导入' if created else '已存在'}：{tid}")
                        st.rerun()
                else: st.caption('信号库为空')
            except Exception as e: st.warning(f'读取信号失败：{e}')
        rows=db.execute('SELECT * FROM topics ORDER BY updated_at DESC,created_at DESC').fetchall()
        c1,c2,c3,c4=st.columns(4)
        c1.metric('总选题',len(rows))
        c2.metric('待审核',sum(r['status']=='pending_review' for r in rows))
        c3.metric('已批准',sum(r['status']=='approved' for r in rows))
        c4.metric('制作中',sum(r['status']=='in_production' for r in rows))
        f1,f2=st.columns(2)
        status=f1.selectbox('状态',['全部']+list(ALLOWED))
        account_filter=f2.selectbox('账号',['全部','Luke 2.0','Amazon x AI','Unassigned'])
        filtered=[r for r in rows if (status=='全部' or r['status']==status) and (account_filter=='全部' or r['account']==account_filter)]
        st.dataframe([{'标题':r['title'],'账号':r['account'],'状态':r['status'],'质量':r['insight_score'],'优先级':r['priority'],'Series':r['series']} for r in filtered],use_container_width=True,hide_index=True)
        if not filtered: return
        chosen=st.selectbox('查看 / 编辑选题',[r['topic_id'] for r in filtered],format_func=lambda tid:next(r['title'] for r in filtered if r['topic_id']==tid))
        row=next(r for r in filtered if r['topic_id']==chosen)
        gate=gate_result(db,chosen)
        st.caption(f"`{row['status']}` · 质量 {row['insight_score'] if row['insight_score'] is not None else '未评'}/35 · {row['priority'] or '未评'} · {gate['reason']}")
        with st.expander('Content Brief · 证据与观点',expanded=True):
            fields=['audience','pain_point','core_insight','hook','evidence','target_action']
            names=['目标受众','用户痛点','核心观点','Hook 草稿','真实证据 / 素材','目标动作']
            with st.form('brief_v11'):
                vals={k:st.text_area(label,value=row[k] or '',height=80) for k,label in zip(fields,names)}
                if st.form_submit_button('保存 Brief'):
                    update_brief(db,chosen,vals);st.success('Brief 已保存');st.rerun()
            if ai_call is not None:
                if st.button('AI 生成 Brief + 初评分'):
                    with st.spinner('分析选题中…'):
                        try:
                            request=json.dumps({'title':row['title'],'account':row['account'],'series':row['series'],'source':row['source_reference'],'existing_brief':{k:row[k] for k in fields}},ensure_ascii=False)
                            raw=ai_call(SYSTEM,request)
                            st.session_state[f'ai_raw_{chosen}']=raw
                            def parse_ai_json(value):
                                value=value.strip()
                                if value.startswith('```'):
                                    value=value.split('\n',1)[-1].rsplit('```',1)[0].strip()
                                return json.loads(value)
                            try:
                                obj=parse_ai_json(raw)
                            except json.JSONDecodeError:
                                # One bounded retry; never silently change or discard the raw answer.
                                retry=ai_call('你是 JSON 格式修复器。仅返回一个合法 JSON 对象，不添加或编造内容；保持字段和值原意。',
                                              '将下面文本转换为合法 JSON；不要使用 Markdown 代码块：\n'+raw[:14000])
                                st.session_state[f'ai_retry_raw_{chosen}']=retry
                                obj=parse_ai_json(retry)
                            q=obj['quality_scores'];p=obj['priority_scores']
                            values={k:int(q[k]) for k in QUALITY}|{k:int(p[k]) for k in PRIORITY}
                            st.session_state.pop(f'ai_edit_{chosen}',None)
                            st.session_state[f'ai_draft_{chosen}']=obj
                            st.session_state[f'ai_scores_{chosen}']=values
                            st.success('AI 草稿已生成；审核后再保存')
                        except Exception as e:
                            st.error(f'AI 分析失败：{e}')
                            st.info('AI 原始响应已保留。可以展开下面的诊断信息，复制后检查；已保存的 Brief 不会受到影响。')
                if st.session_state.get(f'ai_raw_{chosen}'):
                    with st.expander('AI 响应诊断（仅排错时展开）',expanded=False):
                        st.code(st.session_state[f'ai_raw_{chosen}'],language='text')
                        if st.session_state.get(f'ai_retry_raw_{chosen}'):
                            st.caption('自动修复尝试的返回内容')
                            st.code(st.session_state[f'ai_retry_raw_{chosen}'],language='text')
                draft=st.session_state.get(f'ai_draft_{chosen}')
                if draft:
                    st.markdown('#### 编辑 AI 草稿')
                    st.caption('逐项修改后再保存。AI 不会自动覆盖你的编辑；修改后的内容会写入当前选题。')
                    draft_key=f'ai_edit_{chosen}'
                    if draft_key not in st.session_state:
                        st.session_state[draft_key]={k:str(draft.get(k,'') or '') for k in fields+['score_reasoning']}
                    with st.form(f'ai_edit_form_{chosen}'):
                        edited={k:st.text_area(label, value=st.session_state[draft_key].get(k,''), height=110 if k in ('evidence','score_reasoning') else 80, key=f'ai_edit_{chosen}_{k}') for k,label in zip(fields+['score_reasoning'],names+['AI 评分理由 / 可编辑'])}
                        save_edited=st.form_submit_button('保存修改后的 Brief 与 AI 初评分',type='primary')
                    if save_edited:
                        st.session_state[draft_key]=edited.copy()
                        update_brief(db,chosen,{k:edited[k] for k in fields})
                        score(db,chosen,st.session_state[f'ai_scores_{chosen}'])
                        st.session_state.pop(f'ai_draft_{chosen}',None)
                        st.session_state.pop(draft_key,None)
                        st.success('已保存你编辑后的 Brief 和 AI 初评分')
                        st.rerun()
                    if st.button('放弃本次 AI 草稿',key=f'ai_discard_{chosen}'):
                        st.session_state.pop(f'ai_draft_{chosen}',None)
                        st.session_state.pop(draft_key,None)
                        st.rerun()
        with st.expander('评分明细 · 7 + 3',expanded=False):
            existing=db.execute('SELECT * FROM topic_scores WHERE topic_id=?',(chosen,)).fetchone()
            with st.form(f'scores_v11_{chosen}'):
                values={k:st.slider(LABELS[k],0 if k in QUALITY else 1,5 if k in QUALITY else 3,int(existing[k]) if existing else (3 if k in QUALITY else 2)) for k in QUALITY+PRIORITY}
                if st.form_submit_button('保存评分'):
                    result=score(db,chosen,values)
                    st.success(f"质量 {result['quality']}/35 · {result['priority']} · {result['quality_gate']}");st.rerun()
        states=sorted(ALLOWED[row['status']])
        if states:
            st.markdown('#### 审核与状态流转')
            target=st.selectbox('流转到',states)
            reason=st.text_input('搁置原因') if target=='paused' else None
            override=None
            if target=='approved' and not gate['eligible']:
                st.warning('评分门槛未通过：'+gate['reason'])
                override=st.text_area('人工 Override 原因（必须填写才可批准）')
            if st.button('更新状态'):
                try:
                    transition(db,chosen,target,reason,override)
                    st.success('状态已更新');st.rerun()
                except ValueError as e: st.error(str(e))
        if row['status'] in ('approved','scheduled','in_production'):
            if st.button('送入流水线（预填选题）'):
                st.session_state['idea']=row['title']
                st.session_state['topic_active_id']=chosen
                st.info('已预填流水线选题。请点击顶部「流水线」标签继续制作。')
