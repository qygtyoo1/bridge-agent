#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""challenge_l3.py — 挑战-应答型 L3 核验：证明对方"能写自己的站点"，不只是"有张可读的卡"

背景: 自洽性 L3 只能证明"卡片与地址一致且稳定"; 若对方是静态托管, 任何人都可能复制一张卡。
挑战-应答要求对方在**自己的站点**发布一个一次性 nonce 文件 —— 只有能控制该站点(能提交/部署)的人做得到。

用法:
  python challenge_l3.py issue  --card <对方 agent-card URL> [--out challenge.json]
  python challenge_l3.py verify --challenge challenge.json
流程:
  1) issue: 读取对方卡片 → 生成 nonce → 打印对方需要发布的 URL 与文件内容
  2) 对方把 {"nonce", "agent_card_id", "issued_at"} 提交到 <站点目录>/bridge-challenge/<nonce>.json
  3) verify: 回读该文件 → 校验 nonce 一致 / 身份一致 / 时效 ≤72h
零依赖; 只访问对方卡片中声明的地址及其同目录 challeng 文件。
"""
import argparse, json, os, secrets, sys, datetime, urllib.request
from urllib.parse import urljoin

PROTOCOL = "BRIDGE-1.0"
MAX_AGE_H = 72

def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "bridge-agent/challenge_l3"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", errors="replace"))

def base_dir(card_url):
    return urljoin(card_url, "./")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("issue"); i.add_argument("--card", required=True); i.add_argument("--out", default="challenge.json")
    v = sub.add_parser("verify"); v.add_argument("--challenge", default="challenge.json")
    a = ap.parse_args()

    if a.cmd == "issue":
        try:
            st, card = fetch_json(a.card)
        except Exception as e:
            print("读取卡片失败:", e); return 2
        if card.get("schema_version") != PROTOCOL:
            print("FAIL: schema_version != %s" % PROTOCOL); return 2
        nonce = secrets.token_hex(8)
        base = base_dir(a.card)
        rec = {
            "protocol": PROTOCOL, "card_url": a.card, "agent_card_id": card.get("agent_card_id"),
            "nonce": nonce, "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "publish_url": base + "bridge-challenge/%s.json" % nonce,
            "file_content": {"nonce": nonce, "agent_card_id": card.get("agent_card_id"),
                             "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat()},
        }
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        print("挑战已生成:", a.out)
        print("请对方在以下地址发布文件（内容如下）:")
        print("  URL :", rec["publish_url"])
        print("  内容:", json.dumps(rec["file_content"], ensure_ascii=False))
        print("完成后运行: python challenge_l3.py verify --challenge", a.out)
        return 0

    # verify
    try:
        rec = json.load(open(a.challenge, encoding="utf-8"))
    except Exception as e:
        print("读取挑战文件失败:", e); return 2
    url = rec.get("publish_url")
    try:
        st, body = fetch_json(url)
    except Exception as e:
        print("FAIL: 挑战文件不可达:", e); return 1
    errs = []
    if body.get("nonce") != rec.get("nonce"):
        errs.append("nonce 不一致")
    if body.get("agent_card_id") != rec.get("agent_card_id"):
        errs.append("身份不一致: %s != %s" % (body.get("agent_card_id"), rec.get("agent_card_id")))
    try:
        ts = datetime.datetime.fromisoformat(body.get("issued_at").replace("Z", "+00:00"))
        age_h = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 3600
        if age_h > MAX_AGE_H:
            errs.append("挑战过期: %.1fh > %dh" % (age_h, MAX_AGE_H))
    except Exception:
        errs.append("issued_at 非法")
    if errs:
        print("L3-CR FAIL:", "; ".join(errs)); return 1
    print("L3-CR PASS: 对方已在 %s 发布 nonce, 证明其可写自己的站点" % url)
    return 0

if __name__ == "__main__":
    sys.exit(main())
