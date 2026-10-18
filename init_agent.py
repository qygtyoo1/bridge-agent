#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_agent.py — Bridge-Agent 首跑体验：30 秒生成你的登记卡（并可选跑完整演示）

目标: 开发者不需要先读文档, 一条命令拿到「可校验、可发布」的 agent-card + 诉求模板。
用法:
  python init_agent.py --name "我的智能体" --caps a2a_connect,code_review
  python init_agent.py --demo            # 一键演示全流程(生成→校验→匹配→核验)
零第三方依赖; 生成后自动用 validate_sb.py(若同目录存在)做本地校验。
"""
import argparse, json, os, re, subprocess, sys, time, datetime
from datetime import timezone

PROTOCOL = "BRIDGE-1.0"
HERE = os.path.dirname(os.path.abspath(__file__))

def slug(s):
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", "-", s).strip("-").lower()
    return s or "agent"

def make_card(name, caps, endpoint, cid=None):
    return {
        "schema_version": PROTOCOL, "subject_type": "agent",
        "agent_card_id": cid or ("ac_%s_%s" % (slug(name), datetime.datetime.now().strftime("%m%d%H%M"))),
        "name": name, "capabilities": caps, "endpoint": endpoint,
        "permission_boundary": "仅接受已确权通道消息",
        "verify_state": "pending", "index_status": "submitted_pending_merge",
        "protocol_version": PROTOCOL,
    }

def make_appeal(card, purpose="找一位做跨实例协作的开发者, 一起把智能体连起来"):
    return {
        "schema_version": PROTOCOL,
        "appeal_id": "ap_%s" % card["agent_card_id"].replace("ac_", ""),
        "subject_ref": {"card_ref": card["agent_card_id"], "subject_type": "agent"},
        "appeal_type": "collab_dev",
        "published_at": datetime.datetime.now(timezone.utc).isoformat(),
        "status": "active", "lifecycle_days": 90,
        "custom_purpose": purpose, "public_replies": [],
    }

def write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def validate(path):
    v = os.path.join(HERE, "validate_sb.py")
    if not os.path.isfile(v):
        print("  (未找到 validate_sb.py, 跳过本地校验)")
        return True
    r = subprocess.run([sys.executable, v, "--file", path], capture_output=True, text=True)
    ok = r.returncode == 0
    out = (r.stdout or "") + (r.stderr or "")
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    msg = next((l for l in lines if ("PASS" in l.upper() or "FAIL" in l.upper() or "错误" in l or "缺失" in l)), lines[-1] if lines else "")
    print("  %s %s" % ("✓" if ok else "✗", msg[:140]))
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name"); ap.add_argument("--caps", default="a2a_connect")
    ap.add_argument("--endpoint", default="https://example.com/.well-known/agent-card.json")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    if a.demo:
        d = os.path.join(a.outdir, "bridge_demo"); os.makedirs(d, exist_ok=True)
        me = make_card("我的智能体", ["a2a_connect", "code_review"], "https://example.com/.well-known/agent-card.json")
        peer = make_card("数据可视化伙伴", ["a2a_connect", "data_viz"], "https://peer.example.com/.well-known/agent-card.json")
        write(os.path.join(d, "ac_me.json"), me)
        write(os.path.join(d, "ac_peer.json"), peer)
        write(os.path.join(d, "ap_me.json"), make_appeal(me))
        write(os.path.join(d, "ap_peer.json"), make_appeal(peer, "找后端伙伴, 我擅长可视化"))
        with open(os.path.join(d, "cards.jsonl"), "w", encoding="utf-8") as f:
            for c in (me, peer):
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        with open(os.path.join(d, "appeals.jsonl"), "w", encoding="utf-8") as f:
            for c in (me, peer):
                f.write(json.dumps(make_appeal(c, "找跨实例协作伙伴"), ensure_ascii=False) + "\n")
        print("① 已生成演示档案:", d)
        print("② 本地校验:"); validate(os.path.join(d, "ac_me.json")); validate(os.path.join(d, "ac_peer.json"))
        m = os.path.join(HERE, "match_peers.py")
        if os.path.isfile(m):
            print("③ 分层匹配演示:")
            r = subprocess.run([sys.executable, m, "--cards", os.path.join(d, "cards.jsonl"),
                                "--appeals", os.path.join(d, "appeals.jsonl"), "--me", me["agent_card_id"]],
                               capture_output=True, text=True)
            print(r.stdout.strip() or r.stderr.strip())
        print("④ 完成。下一步: 把 ac_me.json 发布到你自己的 HTTPS 端点, 并把地址发给合作方(人牵线)。")
        return 0

    if not a.name:
        print("请提供 --name \"你的智能体名\", 或加 --demo 先看一遍演示")
        return 2
    caps = [c.strip() for c in a.caps.split(",") if c.strip()]
    card = make_card(a.name, caps, a.endpoint)
    card_path = os.path.join(a.outdir, card["agent_card_id"] + ".json")
    appeal_path = os.path.join(a.outdir, card["agent_card_id"] + "_appeal.json")
    write(card_path, card); write(appeal_path, make_appeal(card))
    print("✓ 已生成登记卡:", card_path)
    print("✓ 已生成诉求模板:", appeal_path)
    print("· 本地校验:")
    ok1 = validate(card_path); ok2 = validate(appeal_path)
    print("· 下一步:")
    print("  1) 把 %s 放到你的 HTTPS 站点(如 GitHub Pages), 得到一个可回读的 endpoint;" % card["agent_card_id"])
    print("  2) 用 peer_register.py --card <对方卡地址> 做 L1/L2/L3 核验;")
    print("  3) 双方确认意向(人牵线) → 生成握手凭证。")
    return 0 if (ok1 and ok2) else 1

if __name__ == "__main__":
    sys.exit(main())
