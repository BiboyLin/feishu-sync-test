#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue → Feishu Bitable（field_name 版）
同步字段：
- 标题
- IssueURL（自动）
- 优先级（SingleSelect）
- 需求类型（SingleSelect）
- bug来源（可选）（SingleSelect）
"""
import os, sys, re, json, argparse, requests
from typing import Dict, Any, Optional

BITABLE = "https://open.feishu.cn/open-apis/bitable/v1"
AUTH = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
HEADERS_JSON = {"Content-Type": "application/json; charset=utf-8"}

# === 用“字段名”作为 key（与表中显示完全一致）===
FN = ["标题", "IssueURL", "优先级", "需求类型", "bug来源（可选）"]

PRIORITY_ALIASES = {
    "P0":"P0","0":"P0","HIGH":"P0","H":"P0",
    "P1":"P1","1":"P1","MEDIUM":"P1","M":"P1",
    "P2":"P2","2":"P2","LOW":"P2","L":"P2",
    "P3":"P3","3":"P3",
}
TYPE_ALIASES = {
    "bug":"BUG","缺陷":"BUG",
    "feature":"Feature","新功能":"Feature",
    "enhancement":"Enhancement","优化":"Enhancement","improvement":"Enhancement",
}

def log(s:str): print(f"[sync] {s}", flush=True)

def get_token(app_id:str, app_secret:str)->str:
    r = requests.post(AUTH, headers=HEADERS_JSON,
                      json={"app_id":app_id,"app_secret":app_secret}, timeout=30)
    data = r.json()
    if not data.get("tenant_access_token"):
        raise RuntimeError(f"get token fail: {data}")
    return data["tenant_access_token"]

def parse_md(md:str)->Dict[str,str]:
    out={}
    if not md: return out
    pat=re.compile(r"(^|\n)#{2,3}\s*([^\n#]+?)\s*\n([\s\S]*?)(?=\n#{2,3}\s|$)")
    for m in pat.finditer(md):
        k=(m.group(2) or "").strip()
        v=(m.group(3) or "").strip()
        if k: out[k]=v
    return out

def norm_pri(v:str)->Optional[str]:
    if not v: return None
    s=v.strip().upper()
    return PRIORITY_ALIASES.get(s, v.strip())

def norm_type(v:str)->Optional[str]:
    if not v: return None
    s=v.strip().lower()
    return TYPE_ALIASES.get(s, v.strip().capitalize())

def build_from_issue(evt:Dict[str,Any])->Dict[str,Any]:
    issue=(evt or {}).get("issue") or {}
    body=issue.get("body") or ""
    md=parse_md(body)

    fields:Dict[str,Any]={}
    # 标题（若为空，兜底用 Issue 标题）
    title_md=(md.get("标题") or "").strip()
    fields["标题"]= title_md or (issue.get("title") or "")

    # IssueURL
    if issue.get("html_url"):
        fields["IssueURL"]=issue["html_url"]

    # ✅ 单选字段：传“字符串”，不要传 {"text": "..."}
    pri=norm_pri(md.get("优先级",""))
    if pri: fields["优先级"]=pri

    typ=norm_type(md.get("需求类型",""))
    if typ: fields["需求类型"]=typ

    bug_src=(md.get("bug来源（可选）") or "").strip()
    if bug_src: fields["bug来源（可选）"]=bug_src

    # 只保留关心的五个字段
    fields={k:v for k,v in fields.items() if k in FN}
    return fields

def build_from_inputs(inputs:Dict[str,str], issue_url:str)->Dict[str,Any]:
    fields:Dict[str,Any]={}
    fields["标题"]= (inputs.get("标题","").strip()
                     or inputs.get("Issue标题","").strip())
    fields["IssueURL"]=issue_url.strip()

    # ✅ 单选字段：字符串
    pri=norm_pri(inputs.get("优先级",""))
    if pri: fields["优先级"]=pri

    typ=norm_type(inputs.get("需求类型",""))
    if typ: fields["需求类型"]=typ

    bug_src=(inputs.get("bug来源（可选）") or "").strip()
    if bug_src: fields["bug来源（可选）"]=bug_src

    fields={k:v for k,v in fields.items() if k in FN}
    return fields
def search_record(token:str, app_token:str, table_id:str, issue_url:str)->Optional[str]:
    url=f"{BITABLE}/apps/{app_token}/tables/{table_id}/records/search"
    params={"page_size":1, "filter": f'IssueURL = "{issue_url}"'}
    r=requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
    data=r.json()
    items=((data.get("data") or {}).get("items") or [])
    if items: return items[0]["record_id"]
    return None

def upsert(token:str, app_token:str, table_id:str, fields:Dict[str,Any])->Dict[str,Any]:
    iu=fields.get("IssueURL")
    if not iu: raise ValueError("IssueURL 缺失，无法查重。")

    rec_id=search_record(token, app_token, table_id, iu)
    payload={"fields": fields}

    if rec_id:
        url=f"{BITABLE}/apps/{app_token}/tables/{table_id}/records/{rec_id}"
        r=requests.patch(url, headers={"Authorization": f"Bearer {token}", **HEADERS_JSON},
                         data=json.dumps(payload, ensure_ascii=False), timeout=30)
    else:
        url=f"{BITABLE}/apps/{app_token}/tables/{table_id}/records"
        r=requests.post(url, headers={"Authorization": f"Bearer {token}", **HEADERS_JSON},
                        data=json.dumps(payload, ensure_ascii=False), timeout=30)

    try:
        data=r.json()
    except Exception:
        raise RuntimeError(f"http {r.status_code}: {r.text}")
    if data.get("code") not in (0, None):
        raise RuntimeError(f"upsert error: {data}")
    return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--event", help="本地调试：GitHub issues 事件 JSON 路径")
    args=ap.parse_args()

    app_id=os.environ.get("FEISHU_APP_ID","")
    app_secret=os.environ.get("FEISHU_APP_SECRET","")
    app_token=os.environ.get("FEISHU_APP_TOKEN","")
    table_id=os.environ.get("FEISHU_TABLE_ID","")
    if not all([app_id, app_secret, app_token, table_id]):
        log("❌ 缺少 FEISHU_* 环境变量"); sys.exit(1)

    evt={}
    if args.event and os.path.exists(args.event):
        evt=json.load(open(args.event,"r",encoding="utf-8"))
    elif os.environ.get("GITHUB_EVENT_PATH"):
        evt=json.load(open(os.environ["GITHUB_EVENT_PATH"],"r",encoding="utf-8"))

    if evt.get("issue"):
        fields=build_from_issue(evt)
    else:
        inputs={k:v for k,v in os.environ.items()
                if k in ["标题","优先级","需求类型","bug来源（可选）","Issue标题","IssueURL"]}
        issue_url=inputs.get("IssueURL") or "https://example.com/mock"
        fields=build_from_inputs(inputs, issue_url)

    log(f"fields(payload): {json.dumps(fields, ensure_ascii=False)}")
    token=get_token(app_id, app_secret)
    res=upsert(token, app_token, table_id, fields)
    log(f"done: {json.dumps(res, ensure_ascii=False)}")

if __name__=="__main__":
    main()
