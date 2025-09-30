#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将飞书 Wiki 节点 token（/wiki/<node_token>）解析为 Bitable 的 app_token（/base/<app_token>）
并可选校验该 Base 下是否存在指定 table_id。

用法示例：
  # 方式一：已持有 tenant_access_token
  export TENANT_ACCESS_TOKEN="t-xxxxx"
  python wiki2bitable.py --wiki-url "https://xxx.feishu.cn/wiki/GCFkwFwjLi2lE1kY3EFc15cunH8?table=tblTqPEg9ogOWI5x"

  # 方式二：提供 app_id/secret，由脚本获取 token
  export FEISHU_APP_ID="cli_xxx"
  export FEISHU_APP_SECRET="xxx"
  python wiki2bitable.py --node "GCFkwFwjLi2lE1kY3EFc15cunH8" --table-id "tblTqPEg9ogOWI5x"
"""
import os
import re
import sys
import json
import argparse
import requests

WIKI_GET_NODE = "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node"
BITABLE_GET_BASE = "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}"
BITABLE_LIST_TABLES = "https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
GET_TENANT_TOKEN = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

def get_tenant_token_if_needed() -> str:
    token = os.getenv("TENANT_ACCESS_TOKEN", "").strip()
    if token:
        return token
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        print("❌ 缺少 TENANT_ACCESS_TOKEN，且未提供 FEISHU_APP_ID/FEISHU_APP_SECRET。", file=sys.stderr)
        sys.exit(1)
    resp = requests.post(GET_TENANT_TOKEN, json={"app_id": app_id, "app_secret": app_secret}, timeout=30)
    data = resp.json()
    if not data.get("tenant_access_token"):
        print(f"❌ 获取 tenant_access_token 失败：{data}", file=sys.stderr)
        sys.exit(1)
    return data["tenant_access_token"]

def extract_node_token(wiki_url_or_token: str) -> str:
    s = wiki_url_or_token.strip()
    # 如果是完整 URL，提取 /wiki/<token> 段
    m = re.search(r"/wiki/([A-Za-z0-9]+)", s)
    if m:
        return m.group(1)
    # 否则就当成节点 token 直接用
    return s

def get_node_info(tenant_token: str, node_token: str) -> dict:
    r = requests.get(WIKI_GET_NODE, headers={"Authorization": f"Bearer {tenant_token}"}, params={"token": node_token}, timeout=30)
    try:
        return r.json()
    except Exception:
        return {"http_status": r.status_code, "text": r.text}

def get_base_meta(tenant_token: str, app_token: str) -> dict:
    url = BITABLE_GET_BASE.format(app_token=app_token)
    r = requests.get(url, headers={"Authorization": f"Bearer {tenant_token}"}, timeout=30)
    try:
        return r.json()
    except Exception:
        return {"http_status": r.status_code, "text": r.text}

def list_tables(tenant_token: str, app_token: str) -> dict:
    url = BITABLE_LIST_TABLES.format(app_token=app_token)
    r = requests.get(url, headers={"Authorization": f"Bearer {tenant_token}"}, timeout=30)
    try:
        return r.json()
    except Exception:
        return {"http_status": r.status_code, "text": r.text}

def main():
    ap = argparse.ArgumentParser(description="Wiki node → Bitable app_token 解析器")
    ap.add_argument("--wiki-url", help="完整的 wiki URL（例如 https://xxx.feishu.cn/wiki/<node>?table=tbl...）", default="")
    ap.add_argument("--node", help="或直接提供 wiki node_token（/wiki/<node> 的那串）", default="")
    ap.add_argument("--table-id", help="可选：校验该 table_id 是否在 Base 下（例如 tblTqPEg9ogOWI5x）", default="")
    args = ap.parse_args()

    if not args.wiki_url and not args.node:
        print("❌ 请通过 --wiki-url 或 --node 传入 wiki 节点信息。", file=sys.stderr)
        sys.exit(1)

    node_token = extract_node_token(args.wiki_url or args.node)
    tenant_token = get_tenant_token_if_needed()

    print(f"[+] node_token = {node_token}")

    # 1) 取 wiki 节点信息
    node_info = get_node_info(tenant_token, node_token)
    print(f"[+] wiki.get_node 返回：{json.dumps(node_info, ensure_ascii=False)}")

    if node_info.get("code") != 0:
        print("❌ wiki 节点查询失败，请检查 token/权限/租户是否匹配。", file=sys.stderr)
        sys.exit(2)

    data = node_info.get("data") or {}
    obj_type = data.get("obj_type")
    obj_token = data.get("obj_token")

    if obj_type != "bitable" or not obj_token:
        print(f"❌ 该 wiki 节点不是多维表格（obj_type={obj_type}），无法作为 Bitable Base 使用。", file=sys.stderr)
        sys.exit(3)

    app_token = obj_token
    print(f"[+] 解析得到 app_token = {app_token} （用于 /bitable/v1/apps/{'{app_token}'})")

    # 2) 探针：确认 Base 元信息
    base_meta = get_base_meta(tenant_token, app_token)
    print(f"[+] 探针：Base 元信息：{json.dumps(base_meta, ensure_ascii=False)}")

    if base_meta.get("code") not in (0, None):
        print("❌ 读取 Base 元信息失败：可能是跨租户或权限不足。", file=sys.stderr)
        sys.exit(4)

    # 3) 列出 Base 下所有表，并可选校验 table_id
    tables = list_tables(tenant_token, app_token)
    print(f"[+] 探针：该 Base 下的表列表：{json.dumps(tables, ensure_ascii=False)}")

    if tables.get("code") not in (0, None):
        print("❌ 列表表失败：检查权限/租户。", file=sys.stderr)
        sys.exit(5)

    wanted = args.table_id.strip()
    if wanted:
        items = ((tables.get("data") or {}).get("items") or [])
        has = any(t.get("table_id") == wanted for t in items)
        print(f"[+] 校验 table_id={wanted} 是否存在：{has}")
        if not has:
            print("❌ 指定 table_id 不在该 Base 下，请核对 URL 或权限。", file=sys.stderr)
            sys.exit(6)

    print("\n✅ 成功：请把以上 app_token 用于 /bitable/v1/apps/{app_token} 的后续接口（records/search、create、patch 等）。")

if __name__ == "__main__":
    main()
