#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""peer_register.py — Bridge-Agent 功能1「登记即对接」+ 功能2「自动核验」(L1/L2) 工具化

人牵线合规: 仅访问使用者显式提供的对方 agent-card 地址(不做任何自主发现/漫游)。
用法:
  python peer_register.py --card <对方 agent-card URL> [--ledger peers.jsonl]
核验层级:
  L1 拉取+格式: card 可达且字段符合 BRIDGE-1.0
  L2 端点回读: card.endpoint 可访问 (该地址确实对应一个活的公开站点)
输出: 核验结论 + 本地登记(append-only jsonl, 默认 ./peers.jsonl)
返回码: 0=通过(可进入握手); 1=未通过
仅依赖 Python 标准库。
"""
# --- Hermes 静默化补丁(2026-09-16): 抑制子进程控制台弹窗 ---
import sys as _hq_sys, os as _hq_os; _hq_sys.path.append(_hq_os.path.join(_hq_os.environ.get('LOCALAPPDATA', ''), 'hermes', 'scripts')); import _hermes_quiet  # noqa: E402,F401
# --- /Hermes 静默化补丁 ---
import argparse, json, sys, os, datetime
import urllib.request

PROTOCOL = "BRIDGE-1.0"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bridge-agent/peer_register"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read().decode("utf-8", errors="replace")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, help="对方 agent-card URL (https)")
    ap.add_argument("--ledger", default="peers.jsonl")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = {"card": a.card, "l1": None, "l2": None, "name": None, "errors": []}

    # L1: 拉取 + 格式
    if not a.card.startswith("https://"):
        res["errors"].append("L1 失败: 仅支持 https")
    else:
        try:
            st, body = fetch(a.card)
            card = json.loads(body)
            res["l1"] = (st == 200)
            res["name"] = card.get("name")
            if card.get("schema_version") != PROTOCOL:
                res["errors"].append("L1 失败: schema_version != %s" % PROTOCOL)
                res["l1"] = False
            for f in ("agent_card_id", "name", "endpoint", "capabilities"):
                if not card.get(f):
                    res["errors"].append("L1 失败: 缺字段 %s" % f)
                    res["l1"] = False
        except Exception as e:
            res["l1"] = False
            res["errors"].append("L1 失败: %s" % e)
            card = {}

    # L2: 端点回读
    ep = card.get("endpoint")
    if res["l1"] and ep:
        try:
            st2, _ = fetch(ep)
            res["l2"] = (st2 == 200)
            if st2 != 200:
                res["errors"].append("L2 失败: endpoint HTTP %s" % st2)
        except Exception as e:
            res["l2"] = False
            res["errors"].append("L2 失败: %s" % e)
    else:
        res["l2"] = False if res["l1"] else None

    ok = bool(res["l1"] and res["l2"])
    res["verdict"] = "PASS(可进入人工握手流程)" if ok else "FAIL"
    # 本地登记(append-only)
    entry = {
        "type": "peer_registered", "card_url": a.card, "peer_name": res["name"],
        "l1": res["l1"], "l2": res["l2"], "verdict": res["verdict"],
        "at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "核验通过≠合作确权; 握手仍须双方 human_approval(人牵线铁律)",
    }
    with open(a.ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("[L1] %s | [L2] %s | 对方: %s" % (res["l1"], res["l2"], res["name"]))
        for e in res["errors"]:
            print("  -", e)
        print("结论:", res["verdict"], "| 已登记到", a.ledger)
        if ok:
            print("下一步: 与对方确认意向(人牵线) → 按 SKILL.md 生成握手凭证(双方 human_approval)")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
