#!/usr/bin/env python3
"""Build a deterministic, dependency-free critic score dashboard."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = SKILL_DIR / "data" / "science_skill_catalog.json"
DEFAULT_SCORES = SKILL_DIR / "data" / "science_skill_critic_scores.json"
DEFAULT_OUTPUT = SKILL_DIR / "critic-dashboard.html"

CATALOG_FIELDS = (
    "id",
    "name",
    "summary",
    "domain",
    "subdomain",
    "stage",
    "function",
    "task",
    "classification_rationale",
    "quality_score",
    "readiness",
    "source_repository",
    "source_path",
    "review_status",
)
SCORE_FIELDS = (
    "critic_evidence_level",
    "critic_model",
    "critic_rubric_version",
    "model_source_review_score",
    "model_source_review_verdict",
    "instruction_quality",
    "task_actionability",
    "safety",
    "trigger_clarity",
    "package_maintainability",
    "critic_confidence",
    "critic_skill_type",
    "strengths",
    "risks",
    "evidence",
    "static_validation_status",
    "static_validation_errors",
    "static_validation_warnings",
    "behavior_tested",
    "trigger_tested",
    "evaluation_status",
    "install_recommendation",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indexed(records: object, *, label: str) -> dict[str, dict]:
    if not isinstance(records, list):
        raise ValueError(f"{label} must be an array")
    result: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError(f"{label} records require string id")
        if record["id"] in result:
            raise ValueError(f"duplicate {label} id: {record['id']}")
        result[record["id"]] = record
    return result


def build_payload(catalog_path: pathlib.Path, scores_path: pathlib.Path) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    scores = json.loads(scores_path.read_text(encoding="utf-8"))
    if catalog.get("schema") != "science_skill_catalog_v1":
        raise ValueError("catalog must use science_skill_catalog_v1")
    if scores.get("schema") != "science_skill_critic_scores_v2":
        raise ValueError("scores must use science_skill_critic_scores_v2")

    catalog_by_id = indexed(catalog.get("skills"), label="catalog")
    scores_by_id = indexed(scores.get("scores"), label="score")
    if catalog_by_id.keys() != scores_by_id.keys():
        missing_scores = sorted(catalog_by_id.keys() - scores_by_id.keys())
        missing_catalog = sorted(scores_by_id.keys() - catalog_by_id.keys())
        raise ValueError(
            "catalog/score ID mismatch: "
            f"missing_scores={missing_scores[:5]}, missing_catalog={missing_catalog[:5]}"
        )

    records = []
    for skill_id in sorted(catalog_by_id):
        catalog_record = catalog_by_id[skill_id]
        score_record = scores_by_id[skill_id]
        merged = {key: catalog_record.get(key) for key in CATALOG_FIELDS}
        merged.update({key: score_record.get(key) for key in SCORE_FIELDS})
        behavior = score_record.get("behavior_evaluation") or {}
        trigger = score_record.get("trigger_evaluation") or {}
        provenance = score_record.get("evaluation_provenance") or {}
        merged.update(
            {
                "behavior_status": behavior.get("status"),
                "behavior_pass_rate_delta": behavior.get("pass_rate_delta"),
                "trigger_status": trigger.get("status"),
                "trigger_accuracy": trigger.get("accuracy"),
                "real_execution_evidence": isinstance(
                    provenance.get("execution_evidence"), dict
                ),
            }
        )
        records.append(merged)

    return {
        "schema": "science_skill_critic_dashboard_v1",
        "catalog_sha256": sha256(catalog_path),
        "scores_sha256": sha256(scores_path),
        "records": records,
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">
<title>科研技能评分</title>
<style>
:root{color-scheme:light;--ink:#18201d;--muted:#66706c;--line:#d9dfdc;--paper:#f5f7f6;--white:#fff;--green:#166a4a;--green-soft:#e4f2eb;--amber:#8a5a00;--amber-soft:#fff1ce;--red:#9e2f2f;--red-soft:#fbe7e7;--blue:#285f8f;--blue-soft:#e7f0f8;--focus:#0d6efd}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;letter-spacing:0}button,input,select{font:inherit}button,input,select,[tabindex]{outline-offset:3px}:focus-visible{outline:3px solid var(--focus)}
header{background:#173d32;color:#fff;border-bottom:4px solid #d5ad45}.head{max-width:1480px;margin:auto;padding:20px 24px 18px;display:flex;align-items:end;justify-content:space-between;gap:20px}.title h1{font-size:25px;margin:0 0 4px}.title p{margin:0;color:#d7e4df}.source{font-size:12px;color:#bdd0c9;text-align:right;overflow-wrap:anywhere}
main{max-width:1480px;margin:auto;padding:18px 24px 40px}.metrics{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));border:1px solid var(--line);background:var(--white)}.metric{padding:14px 16px;border-right:1px solid var(--line)}.metric:last-child{border:0}.metric strong{display:block;font-size:24px}.metric span{color:var(--muted)}
.controls{margin-top:14px;padding:14px 0;border-block:1px solid var(--line);display:grid;grid-template-columns:minmax(220px,2fr) repeat(5,minmax(130px,1fr)) auto;gap:10px}.field label{display:block;font-size:12px;font-weight:700;margin-bottom:5px}.field input,.field select{width:100%;height:38px;border:1px solid #bcc6c1;background:#fff;padding:0 10px;border-radius:4px}.reset{align-self:end;height:38px;border:1px solid #9da9a3;background:#fff;border-radius:4px;padding:0 14px;cursor:pointer}.reset:hover{background:#edf1ef}
.workspace{display:grid;grid-template-columns:minmax(0,1fr) 390px;gap:16px;margin-top:16px}.results{min-width:0}.summary-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px}.summary-row h2{font-size:16px;margin:0}.summary-row span{color:var(--muted)}
.distribution{display:flex;height:10px;background:#e4e8e6;margin:0 0 14px;overflow:hidden}.distribution span{min-width:1px}.dist-complete{background:var(--green)}.dist-action{background:#d39a21}.dist-fail{background:#bc4b4b}.dist-other{background:#7391a8}
.table-wrap{background:#fff;border:1px solid var(--line);overflow:auto}table{width:100%;border-collapse:collapse;min-width:930px}th{position:sticky;top:0;background:#eef2f0;text-align:left;font-size:12px;padding:10px;border-bottom:1px solid var(--line);z-index:1}td{padding:10px;border-bottom:1px solid #e8ecea;vertical-align:top}tbody tr{cursor:pointer}tbody tr:hover,tbody tr[aria-selected="true"]{background:#f1f7f4}.name{font-weight:700}.sub{font-size:12px;color:var(--muted);margin-top:2px}.score{font-variant-numeric:tabular-nums;font-weight:700}.badge{display:inline-block;padding:2px 7px;border-radius:999px;font-size:12px;white-space:nowrap}.good{color:var(--green);background:var(--green-soft)}.warn{color:var(--amber);background:var(--amber-soft)}.bad{color:var(--red);background:var(--red-soft)}.info{color:var(--blue);background:var(--blue-soft)}
.more{display:block;margin:12px auto 0;border:1px solid #82918a;background:#fff;border-radius:4px;padding:8px 18px;cursor:pointer}.more[hidden]{display:none}.empty{padding:40px;text-align:center;color:var(--muted)}
.detail{background:#fff;border:1px solid var(--line);position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto}.detail-head{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;gap:12px;justify-content:space-between;align-items:start}.detail h2{font-size:18px;margin:0;overflow-wrap:anywhere}.close{border:0;background:transparent;font-size:20px;line-height:1;cursor:pointer}.detail-body{padding:16px}.detail-body h3{font-size:13px;margin:18px 0 7px;text-transform:none}.detail-body p{margin:5px 0}.detail-body ul{margin:5px 0;padding-left:20px}.detail-body code{white-space:normal;overflow-wrap:anywhere}.score-grid{display:grid;grid-template-columns:1fr auto;gap:5px 10px;padding:10px 0;border-block:1px solid var(--line)}.placeholder{color:var(--muted);padding:28px 16px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:1080px){.controls{grid-template-columns:repeat(3,1fr)}.field.search{grid-column:span 2}.workspace{grid-template-columns:1fr}.detail{position:fixed;inset:0 0 0 auto;width:min(420px,100%);max-height:none;z-index:5;box-shadow:-10px 0 30px #0002}.detail[data-empty="true"]{display:none}}
@media(max-width:680px){.head{padding:16px;display:block}.source{text-align:left;margin-top:10px}.title h1{font-size:21px}main{padding:12px}.metrics{grid-template-columns:repeat(2,1fr)}.metric{border-bottom:1px solid var(--line)}.metric:nth-child(2n){border-right:0}.metric:last-child{grid-column:span 2}.controls{grid-template-columns:1fr 1fr}.field.search{grid-column:span 2}.reset{width:100%}.summary-row{align-items:start}.workspace{margin-top:12px}table{min-width:0;table-layout:fixed}th:nth-child(3),td:nth-child(3),th:nth-child(4),td:nth-child(4),th:nth-child(5),td:nth-child(5),th:nth-child(6),td:nth-child(6){display:none}th:first-child,td:first-child{width:42%}th:nth-child(2),td:nth-child(2){width:36%}th:nth-child(7),td:nth-child(7){width:22%}td{padding:10px 8px;overflow-wrap:anywhere}.detail{width:100%}}
</style>
</head>
<body>
<header><div class="head"><div class="title"><h1>科研技能评分</h1><p>源码评审、静态验证与真实行为证据分层展示</p></div><div class="source" id="sourceMeta"></div></div></header>
<main>
  <section class="metrics" aria-label="评分概览" id="metrics"></section>
  <section class="controls" aria-label="筛选条件">
    <div class="field search"><label for="search">搜索技能或任务</label><input id="search" type="search" placeholder="名称、摘要、原子任务"></div>
    <div class="field"><label for="domain">领域</label><select id="domain"></select></div>
    <div class="field"><label for="stage">研究阶段</label><select id="stage"></select></div>
    <div class="field"><label for="function">功能分工</label><select id="function"></select></div>
    <div class="field"><label for="evidenceLevel">证据层级</label><select id="evidenceLevel"></select></div>
    <div class="field"><label for="recommendation">安装建议</label><select id="recommendation"></select></div>
    <button class="reset" id="reset" type="button">重置</button>
  </section>
  <div class="workspace">
    <section class="results"><div class="summary-row"><h2>技能清单</h2><span id="resultCount"></span></div><div class="distribution" id="distribution" aria-label="当前结果状态分布"></div><div class="table-wrap"><table><thead><tr><th>技能</th><th>领域 / 阶段</th><th>功能</th><th>源码分</th><th>证据</th><th>评测状态</th><th>安装建议</th></tr></thead><tbody id="rows"></tbody></table><div class="empty" id="empty" hidden>没有符合当前条件的技能。</div></div><button class="more" id="more" type="button">显示更多</button></section>
    <aside class="detail" id="detail" data-empty="true" aria-live="polite"><div class="placeholder">选择一个技能查看评分依据、风险和来源。</div></aside>
  </div>
</main>
<script id="dashboardData" type="application/json">__DATA__</script>
<script>
const payload=JSON.parse(document.getElementById('dashboardData').textContent);const records=payload.records;
const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={full_source:'完整源码',metadata_only:'仅元数据',complete:'真实闭环',needs_behavior:'缺行为证据',needs_behavior_and_trigger:'缺行为与触发',provisional_behavior_and_trigger:'暂定结果',static_failed:'静态失败',security_failed:'安全失败',unverified:'未验证',recommend_install:'建议安装',fix_first:'先修复',not_yet_evaluated:'待评测',reject:'拒绝',pass:'通过',fail:'失败',unverifiable:'无法验证'};
const label=v=>labels[v]||v||'未记录';const tone=v=>v==='complete'||v==='recommend_install'||v==='pass'?'good':v==='reject'||v==='security_failed'||v==='static_failed'||v==='fail'?'bad':v==='full_source'?'info':'warn';
let limit=100,selected=null;
function options(id,key){const values=[...new Set(records.map(r=>r[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN'));$(id).innerHTML='<option value="">全部</option>'+values.map(v=>`<option value="${esc(v)}">${esc(label(v))}</option>`).join('')}
function metric(name,value){return `<div class="metric"><strong>${value}</strong><span>${name}</span></div>`}
function init(){options('domain','domain');options('stage','stage');options('function','function');options('evidenceLevel','critic_evidence_level');options('recommendation','install_recommendation');const count=k=>records.filter(k).length;$('metrics').innerHTML=metric('技能总数',records.length)+metric('完整源码评审',count(r=>r.critic_evidence_level==='full_source'))+metric('静态验证通过',count(r=>r.static_validation_status==='pass'))+metric('真实行为闭环',count(r=>r.evaluation_status==='complete'))+metric('建议安装',count(r=>r.install_recommendation==='recommend_install'));$('sourceMeta').textContent=`catalog ${payload.catalog_sha256.slice(0,12)} / scores ${payload.scores_sha256.slice(0,12)}`;render()}
function filtered(){const q=$('search').value.trim().toLowerCase(),domainValue=$('domain').value,stageValue=$('stage').value,functionValue=$('function').value,evidenceValue=$('evidenceLevel').value,recommendationValue=$('recommendation').value;return records.filter(r=>(!q||[r.id,r.name,r.summary,r.task,r.subdomain].some(v=>String(v||'').toLowerCase().includes(q)))&&(!domainValue||r.domain===domainValue)&&(!stageValue||r.stage===stageValue)&&(!functionValue||r.function===functionValue)&&(!evidenceValue||r.critic_evidence_level===evidenceValue)&&(!recommendationValue||r.install_recommendation===recommendationValue)).sort((a,b)=>{const rank={recommend_install:0,not_yet_evaluated:1,fix_first:2,reject:3,unverified:4};return (rank[a.install_recommendation]??5)-(rank[b.install_recommendation]??5)||(b.model_source_review_score??-1)-(a.model_source_review_score??-1)||a.id.localeCompare(b.id)})}
function render(){const list=filtered();$('resultCount').textContent=`${list.length} / ${records.length}`;const shown=list.slice(0,limit);$('rows').innerHTML=shown.map(r=>`<tr tabindex="0" role="button" data-id="${esc(r.id)}" aria-selected="${r.id===selected}"><td><div class="name">${esc(r.name||r.id)}</div><div class="sub">${esc(r.id)}</div></td><td>${esc(r.domain)}<div class="sub">${esc(r.stage)} · ${esc(r.subdomain)}</div></td><td>${esc(r.function)}<div class="sub">${esc(r.task)}</div></td><td class="score">${r.model_source_review_score??'—'}</td><td><span class="badge ${tone(r.critic_evidence_level)}">${esc(label(r.critic_evidence_level))}</span></td><td><span class="badge ${tone(r.evaluation_status)}">${esc(label(r.evaluation_status))}</span></td><td><span class="badge ${tone(r.install_recommendation)}">${esc(label(r.install_recommendation))}</span></td></tr>`).join('');$('empty').hidden=list.length!==0;$('more').hidden=list.length<=limit;$('more').textContent=`显示更多（剩余 ${Math.max(0,list.length-limit)}）`;renderDistribution(list)}
function renderDistribution(list){const groups=[['dist-complete',r=>r.evaluation_status==='complete'],['dist-action',r=>['needs_behavior','needs_behavior_and_trigger','provisional_behavior_and_trigger'].includes(r.evaluation_status)],['dist-fail',r=>['static_failed','security_failed'].includes(r.evaluation_status)],['dist-other',()=>true]];let used=new Set();$('distribution').innerHTML=groups.map(([cls,pred],i)=>{const n=list.filter((r,x)=>!used.has(x)&&pred(r)&&(used.add(x)||true)).length;return `<span class="${cls}" style="width:${list.length?100*n/list.length:0}%" title="${n} 个"></span>`}).join('')}
function list(items,empty='无'){return Array.isArray(items)&&items.length?`<ul>${items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:`<p>${empty}</p>`}
function showDetail(id){selected=id;const r=records.find(x=>x.id===id);if(!r)return;const dimensions=[['指令质量',r.instruction_quality],['任务可执行性',r.task_actionability],['安全性',r.safety],['触发清晰度',r.trigger_clarity],['包维护性',r.package_maintainability]];$('detail').dataset.empty='false';$('detail').innerHTML=`<div class="detail-head"><div><h2>${esc(r.name||r.id)}</h2><div class="sub">${esc(r.domain)} · ${esc(r.stage)} · ${esc(r.function)}</div></div><button class="close" type="button" aria-label="关闭详情">×</button></div><div class="detail-body"><p>${esc(r.summary)}</p><p><span class="badge ${tone(r.install_recommendation)}">${esc(label(r.install_recommendation))}</span> <span class="badge ${tone(r.evaluation_status)}">${esc(label(r.evaluation_status))}</span></p><h3>源码评分</h3><div class="score-grid">${dimensions.map(([k,v])=>`<span>${k}</span><strong>${v??'—'}</strong>`).join('')}</div><h3>行为与触发证据</h3><div class="score-grid"><span>行为评测</span><strong>${esc(label(r.behavior_status))}</strong><span>行为提升</span><strong>${r.behavior_pass_rate_delta??'—'}</strong><span>触发评测</span><strong>${esc(label(r.trigger_status))}</strong><span>触发准确率</span><strong>${r.trigger_accuracy??'—'}</strong><span>真实执行归档</span><strong>${r.real_execution_evidence?'是':'否'}</strong></div><h3>优势</h3>${list(r.strengths)}<h3>风险与限制</h3>${list(r.risks)}<h3>评分证据</h3>${list(r.evidence)}<h3>分类与来源</h3><p>${esc(r.classification_rationale||'未记录分类理由')}</p><p><strong>仓库：</strong><code>${esc(r.source_repository||'未记录')}</code></p><p><strong>路径：</strong><code>${esc(r.source_path||'未记录')}</code></p><p><strong>复核状态：</strong>${esc(r.review_status||'未记录')}</p></div>`;$('detail').querySelector('.close').focus();render()}
document.addEventListener('input',e=>{if(e.target.matches('input,select')){limit=100;render()}});$('reset').addEventListener('click',()=>{document.querySelectorAll('.controls input,.controls select').forEach(x=>x.value='');limit=100;render()});$('more').addEventListener('click',()=>{limit+=100;render()});$('rows').addEventListener('click',e=>{const row=e.target.closest('tr[data-id]');if(row)showDetail(row.dataset.id)});$('rows').addEventListener('keydown',e=>{const row=e.target.closest('tr[data-id]');if(row&&(e.key==='Enter'||e.key===' ')){e.preventDefault();showDetail(row.dataset.id)}});$('detail').addEventListener('click',e=>{if(e.target.closest('.close')){$('detail').dataset.empty='true';$('detail').innerHTML='<div class="placeholder">选择一个技能查看评分依据、风险和来源。</div>';selected=null;render()}});init();
</script>
</body></html>
'''


def render(payload: dict) -> str:
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    embedded = embedded.replace("<", "\\u003c")
    return HTML_TEMPLATE.replace("__DATA__", embedded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--scores", default=str(DEFAULT_SCORES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    try:
        payload = build_payload(pathlib.Path(args.catalog), pathlib.Path(args.scores))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(payload), encoding="utf-8", newline="\n")
    print(f"Wrote {len(payload['records'])} records to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
