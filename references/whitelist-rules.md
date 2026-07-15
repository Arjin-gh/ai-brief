# 公司 AI 白名单交叉检查规则

> 只有当 §3.1 Step A canonical 拉取里对应的白名单条目 `status == "found"` 时，才走本文件。读不到白名单则整段跳过（SKILL.md §3.1 Step C 会写 notices 提示用户）。

## 4 档处理

对每个项目 `current_stack` 里的每个模型，按白名单里的状态输出提示：

| stack 模型状态 | agent 处理 |
|---|---|
| ✅ Approved | 正常，无需提示 |
| 🟡 Under Review | 报告顶部**注意事项**黄色提示："X 尚未正式批准，请与 AI 平台组确认" |
| ⚠️ 不在白名单 | "X 未在公司 AI 白名单，可能存在合规风险" |
| ❌ Not Approved | "X 未获批准使用，请立即评估切换"（措辞更明确） |

**这是 soft warning**（提醒但不紧急），不 urgent/红。合规不匹配对用户重要，但周报里通常不算 red-alert。

## 双过滤（推荐）

- 任何在 `business_impact` / `action_items` / `tech_detail` 里当建议提出来的模型名必须在 Approved 名单内。
- 若 Azure 退役日历推荐 X 作为替代但 X 不在白名单 → 两句都写："官方推荐 X（尚未列入公司白名单，需先申请审批），当前白名单内的替代方案是 Y"。
