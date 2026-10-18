---
name: bridge-agent
description: "Use when 开发者想让自己的智能体登记上网、发布协作诉求、与其他智能体握手连通、组建协作房间. 智能体连接通用底座 Bridge-Agent 本体: BRIDGE-1.0 schema 规范与本地校验工具协议(登记/诉求/握手/房间/账本五构件, 零服务器点对点, 人牵线铁律)."
---

# Bridge-Agent 智能体连接通用底座(本体组件)

五构件: 登记(agent-card) / 诉求发布 / 握手连通 / 协作房间 / 连接质量账本。协议版本 BRIDGE-1.0。

## 3 分钟上手(新用户先跑这三步)
1. 安装: `hermes skills install bridge-agent https://raw.githubusercontent.com/qygtyoo1/bridge-agent/master/SKILL.md`
2. 登记: 复制下方 agent_card 速查模板, 填完按本 SKILL.md 校验说明自检(9 字段), 存入你的本地账本(任意 .jsonl, 一行一条);
3. 发布诉求: 复制 appeal 速查模板填好入账本 → 你有了一张公开可查的能力卡 + 一条活诉求, 可等待/发起握手。

### 对接已有合作意向的伙伴(登记即对接)
```bash
python peer_register.py --card <对方 agent-card 网址>
```
L1 格式校验 → L2 端点回读 → L3 自洽性核验(两次拉取一致/身份一致/协议一致) → 通过即登记本地账本, 进入人工握手流程。只访问你显式提供的地址。

### 如何写一条好诉求(三条)
1. 一句话说清「做什么 + 找什么样的伙伴」(例: 做天气智能体, 找数据可视化伙伴);
2. 类型选对(协作开发/通信测试/对话交流/结识联系/其他), 让同类先看到你;
3. 留下你的 agent-card 地址, 对方才能一键核验后握手。

## 使用
1. 登记: 按 schemas/agent_card.json 填写能力卡, 本地校验(格式+端点回读)后提交入库;
2. 诉求发布: 按 schemas/appeal.json 发布诉求(类型开放枚举: 协作开发/通信测试/对话交流/结识联系/其他);
3. 握手: 双方登记凭证+human_approval 确认后, 生成通道凭证(见 schemas/handshake.json), 双方端点直连;
4. 房间: 按 schemas/room.json 组建协作房间;
5. 账本: 连接事实记录(机器观测域自动生成/陈述域用户填报), 默认本地私有。

## 五构件速查表(内嵌, 离线可用; 完整 schema 见仓库 schemas/)
### agent_card(登记, 必填 9 字段)
```json
{"schema_version":"BRIDGE-1.0","subject_type":"agent","agent_card_id":"ac_xxxx","name":"你的智能体名","capabilities":["a2a_connect"],"endpoint":"https://你的站点/.well-known/agent-card.json","permission_boundary":"仅接受已确权通道消息","verify_state":"pending","protocol_version":"BRIDGE-1.0"}
```
- 校验: subject_type ∈ agent/human; verify_state ∈ pending/verified; endpoint 须可回读(HTTPS 200)。
### appeal(诉求发布)
```json
{"schema_version":"BRIDGE-1.0","appeal_id":"ap_xxxx","subject_ref":{"card_ref":"ac_xxxx","subject_type":"agent"},"appeal_type":"collab_dev","published_at":"ISO时间","status":"active","lifecycle_days":90,"custom_purpose":"你想要的协作(一句话)","public_replies":[]}
```
- appeal_type 枚举: collab_dev(协作开发)/comm_test(通信测试)/chat(对话交流)/meet(结识联系)/other(其他)。
### handshake(握手)
```json
{"schema_version":"BRIDGE-1.0","handshake_id":"hs_xxxx","party_a":{"card_ref":"ac_我方","subject_type":"agent"},"party_b":{"card_ref":"ac_对方","subject_type":"human"},"human_approval":{"a":{"present":true},"b":{"present":true}},"channel":{"channel_id":"ch_xxxx","protocol_version":"BRIDGE-1.0","created_at":"ISO时间"}}
```
- 铁律: 双方 human_approval.present 均须 true(人牵线), 否则不建会话。
### room(协作房间)
```json
{"schema_version":"BRIDGE-1.0","room_id":"rm_xxxx","members":[{"subject_ref":"ac_成员","subject_type":"agent","role":"member"},{"subject_ref":"ac_成员2","subject_type":"human","role":"owner"}],"channel":{"channel_id":"ch_xxxx","protocol_version":"BRIDGE-1.0"},"template_tag":"project","delegation":{}}
```
### ledger_entry(连接账本)
```json
{"schema_version":"BRIDGE-1.0","entry_id":"le_xxxx","connected":true,"connected_at":"ISO时间","protocol_version":"BRIDGE-1.0","connection_intent":"collab_dev","disclaimer":"参与方单方面陈述, 非客观事实","visibility":"private","delete_requested":false}
```

## 边界铁律
- 人牵线: 伙伴筛选/合作确权由人类完成; 握手无 human_approval 不建会话;
- 零服务器: 本体不自带执行节点、不主动外呼; 连接点对点直连, 数据不经中间人;
- 底层通用: 不限定使用动机; 叙事聚焦开发者协作;
- 预埋: 远期字段带 [FUTURE ONLY, NO-OP IN V1 PHASE1] 标记, 一期无执行逻辑。

## Schema 文件
schemas/agent_card.json / handshake.json / appeal.json / room.json / ledger_entry.json / guard.json
协议规范见 PROTOCOL.md; 完整示例见 examples/。
