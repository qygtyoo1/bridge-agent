#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""match_peers.py — Bridge-Agent Phase T2「分层筛选匹配」最小可用实现

漏斗(三级): 候选池(全部登记卡) → 意愿过滤(活跃诉求) → 志同道合匹配(能力互补+诉求类型+关键词)
用法:
  python match_peers.py --cards agent_cards.jsonl --appeals appeals.jsonl --me ac_my_id [--need "关键词"] [--top 5] [--json]
零依赖; 纯本地计算, 不联网, 不采集。
"""
import argparse, json, sys

def load(path):
    rows = []
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except OSError:
        pass
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    ap.add_argument("--appeals", required=True)
    ap.add_argument("--me", required=True, help="我的 agent_card_id")
    ap.add_argument("--need", default="", help="我的目标关键词(可选)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    cards = load(a.cards)
    appeals = load(a.appeals)
    by_id = {c.get("agent_card_id"): c for c in cards if c.get("agent_card_id")}
    me = by_id.get(a.me)
    if not me:
        print("未找到我的登记卡:", a.me)
        return 2
    my_caps = set(me.get("capabilities") or [])

    # ① 候选池: 全部登记卡(去自身); ② 意愿过滤: 有 active 诉求
    active = {}
    for ap_ in appeals:
        if ap_.get("status") != "active":
            continue
        ref = (ap_.get("subject_ref") or {}).get("card_ref")
        if ref:
            active[ref] = ap_

    funnel = {"candidates": len([c for c in cards if c.get("agent_card_id") != a.me]),
              "willing": len(active)}

    scored = []
    for cid, ap_ in active.items():
        if cid == a.me or cid not in by_id:
            continue
        card = by_id[cid]
        caps = set(card.get("capabilities") or [])
        overlap = len(my_caps & caps)
        union = len(my_caps | caps) or 1
        cap_score = overlap / union
        purpose = (ap_.get("custom_purpose") or "")
        kw_hit = 1 if (a.need and a.need in purpose) else 0
        type_score = 1 if ap_.get("appeal_type") in ("collab_dev", "comm_test") else 0
        score = round(0.5 * cap_score + 0.3 * type_score + 0.2 * kw_hit, 3)
        reasons = []
        if overlap:
            reasons.append("能力重叠:" + ",".join(sorted(my_caps & caps)))
        if type_score:
            reasons.append("诉求类型:" + str(ap_.get("appeal_type")))
        if kw_hit:
            reasons.append("关键词命中:" + a.need)
        scored.append({"card_ref": cid, "name": card.get("name", "?"), "score": score,
                       "appeal_type": ap_.get("appeal_type"), "purpose": purpose[:60],
                       "reasons": reasons})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[: a.top]

    if a.json:
        print(json.dumps({"funnel": funnel, "matches": top}, ensure_ascii=False, indent=2))
    else:
        print("漏斗: 候选池 %d → 有意愿 %d → 匹配 %d(展示 %d)" % (
            funnel["candidates"], funnel["willing"], len(scored), len(top)))
        for i, m in enumerate(top, 1):
            print("  %d. %s (%.3f) | %s | %s" % (i, m["name"], m["score"],
                  m["appeal_type"], "; ".join(m["reasons"]) or "无重叠"))
        if not top:
            print("  (当前无可匹配对象: 候选池或诉求为空——先发招募/诉求才能被匹配)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
