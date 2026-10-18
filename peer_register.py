#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""peer_register.py — Bridge-Agent 功能1「登记即对接」+ 功能2「自动核验」(L1/L2/L3)

人牵线合规: 仅访问使用者显式提供的对方 agent-card 地址(不做任何自主发现/漫游)。
用法:
  python peer_register.py --card <对方 agent-card URL> [--ledger peers.jsonl]
核验层级:
  L1 拉取+格式: card 可达且字段符合 BRIDGE-1.0
  L2 端点回读: card.endpoint 可访问 (该地址确实对应一个活的公开站点)
  L3 自洽性核验: ①card 两次拉取(带缓存穿透)内容一致(稳定性) ②endpoint 若为 JSON, 其
     agent_card_id 必须与 card 一致(身份不自相矛盾) ③protocol_version 必须匹配
输出: 核验结论 + 本地登记(append-only jsonl, 默认 ./peers.jsonl)
返回码: 0=通过(可进入握手); 1=未通过
仅依赖 Python 标准库。
"""
# --- Hermes 静默化补丁(2026-09-16): 抑制子进程控制台弹窗 ---
import sys as _hq_sys, os as _hq_os; _hq_sys.path.append(_hq_os.path.join(_hq_os.environ.get('LOCALAPPDATA', ''), 'hermes', 'scripts')); import _hermes_quiet  # noqa: E402,F401
# --- /Hermes 静默化补丁 ---
import argparse, json, sys, os, datetime, hashlib, time
import urllib.request

PROTOCOL = "BRIDGE-1.0"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bridge-agent/peer_register"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read().decode("utf-8", errors="replace")

def cache_bust(url):
    sep = "&" if "?" in url else "?"
    return "%s%st=%d" % (url, sep, int(time.time() * 1000))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, help="对方 agent-card URL (https)")
    ap.add_argument("--ledger", default="peers.jsonl")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = {"card": a.card, "l1": None, "l2": None, "l3": None, "name": None, "errors": []}
    card = {}

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

    # L2: 端点回读
    ep = card.get("endpoint")
    ep_body = ""
    if res["l1"] and ep:
        try:
            st2, ep_body = fetch(ep)
            res["l2"] = (st2 == 200)
            if st2 != 200:
                res["errors"].append("L2 失败: endpoint HTTP %s" % st2)
        except Exception as e:
            res["l2"] = False
            res["errors"].append("L2 失败: %s" % e)
    else:
        res["l2"] = False if res["l1"] else None

    # L3: 自洽性核验(稳定性 + 身份一致 + 协议一致)
    if res["l1"] and res["l2"]:
        try:
            st3, body2 = fetch(cache_bust(a.card))
            h1 = hashlib.sha256(json.dumps(card, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            try:
                card2 = json.loads(body2)
                h2 = hashlib.sha256(json.dumps(card2, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            except Exception:
                h2 = ""
            stable = (st3 == 200 and h1 == h2)
            id_ok = True
            if ep_body.strip().startswith("{"):
                try:
                    ep_json = json.loads(ep_body)
                    ep_id = ep_json.get("agent_card_id")
                    id_ok = (ep_id == card.get("agent_card_id"))
                    if not id_ok:
                        res["errors"].append("L3 失败: endpoint 身份(%s) 与 card 身份(%s) 不一致" % (ep_id, card.get("agent_card_id")))
                except Exception:
                    id_ok = True  # 非结构化 JSON, 交由 L2 判定可达性
            proto_ok = (card.get("protocol_version") == PROTOCOL)
            if not proto_ok:
                res["errors"].append("L3 失败: protocol_version != %s" % PROTOCOL)
            res["l3"] = bool(stable and id_ok and proto_ok)
            if not stable:
                res["errors"].append("L3 失败: card 两次拉取内容不一致(不稳定)")
        except Exception as e:
            res["l3"] = False
            res["errors"].append("L3 失败: %s" % e)
    else:
        res["l3"] = False if res["l1"] else None

    ok = bool(res["l1"] and res["l2"] and res["l3"])
    res["verdict"] = "PASS(可进入人工握手流程)" if ok else "FAIL"
    entry = {
        "type": "peer_registered", "card_url": a.card, "peer_name": res["name"],
        "l1": res["l1"], "l2": res["l2"], "l3": res["l3"], "verdict": res["verdict"],
        "at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "核验通过≠合作确权; 握手仍须双方 human_approval(人牵线铁律)",
    }
    with open(a.ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("[L1] %s | [L2] %s | [L3] %s | 对方: %s" % (res["l1"], res["l2"], res["l3"], res["name"]))
        for e in res["errors"]:
            print("  -", e)
        print("结论:", res["verdict"], "| 已登记到", a.ledger)
        if ok:
            print("下一步: 与对方确认意向(人牵线) → 按 SKILL.md 生成握手凭证(双方 human_approval)")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
