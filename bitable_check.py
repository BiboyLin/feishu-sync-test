#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, requests, argparse

def req_get(url, token, params=None):
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
    try: return r.json()
    except: return {"http_status": r.status_code, "text": r.text}

def req_post(url, token, payload):
    r = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type":"application/json"},
                      data=json.dumps(payload, ensure_ascii=False), timeout=30)
    try: return r.json()
    except: return {"http_status": r.status_code, "text": r.text}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-token", required=True, help="Bitable app_token")
    ap.add_argument("--table-id", required=True, help="table_id (tbl...)")
    ap.add_argument("--issue-url", default="https://github.com/you/repo/issues/123")
    ap.add_argument("--create", action="store_true", help="create a minimal record")
    args = ap.parse_args()

    token = os.environ.get("TENANT_ACCESS_TOKEN") or ""
    if not token:
        print("❌ set TENANT_ACCESS_TOKEN first", file=sys.stderr); sys.exit(1)

    base = req_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{args.app_token}", token)
    print("Base meta:", json.dumps(base, ensure_ascii=False))
    tables = req_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{args.app_token}/tables", token)
    print("Tables:", json.dumps(tables, ensure_ascii=False))

    if args.create:
        payload = {"fields":{
            "标题":"连通性自测（脚本）",
            "Issue标题":"[需求] 移动端登录页异常跳转",
            "IssueURL":args.issue_url,
            "优先级":"P1",
            "需求类型":"BUG",
            "bug来源（可选）":"用户反馈"
        }}
        res = req_post(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{args.app_token}/tables/{args.table_id}/records",
                       token, payload)
        print("Create:", json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()
