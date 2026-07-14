# Canonical Sources — ai-brief

> **agent 每次生成周报前，尝试 fetch 本文件所有 URL，把每个源的可达/不可达情况透明写入 brief.json 的 coverage 段。**
> 读不到就跳，不阻塞流程。规则详见 [`SKILL.md`](../SKILL.md) §3。

本文件把 canonical 源分两类：**公开源** agent 都能读；**组织内源**取决于用户 agent 的认证能力（MCP / cookie / browser tool 等）。

---

## 一、公开源（agent 都应能 fetch）

| 用途 | URL | 覆盖 |
|---|---|---|
| **模型退役日历** | https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule | OpenAI (GPT-4o/5.x/o 系列)、Anthropic Claude、DeepSeek、xAI Grok、Meta Llama、Cohere、Mistral、MoonshotAI |

## 二、组织内源（authenticated · 看用户 agent 能力）

> ⚠️ **本节是示例格式**。下面这条是占位符，请替换为你自己组织的 AI 白名单/模型审批清单 URL。工具不携带任何组织内部 URL。

| 用途 | URL | 覆盖 | 说明 |
|---|---|---|---|
| **AI 模型白名单**（你的组织） | `<替换为你组织的白名单 URL，例如 https://<your-org>.sharepoint.com/sites/AIResourceCenter/...>` | 你组织内部批准可用的 AI 平台与模型清单 | 通常在 SharePoint / Confluence / Notion / 内网 wiki 上。用户 agent 如挂了对应 MCP / 有认证 fetch 能力就能读；否则跳过 |

## 三、用户追加区

<!-- 用户可以在这里补自己关心的 canonical 源。格式跟上面表格保持一致。
| 用途 | URL | 覆盖 | 说明 |
|---|---|---|---|
| OpenAI 官方 deprecation | https://platform.openai.com/docs/deprecations | OpenAI | 公开 |
| Anthropic model retirements | https://docs.anthropic.com/en/docs/about-claude/model-deprecations | Anthropic | 公开 |
| 阿里云 DashScope 版本 | https://help.aliyun.com/zh/dashscope/developer-reference/model-list | 阿里通义 | 公开 |
-->

（暂无）

---

## 使用规则

### 1. 尝试 fetch 顺序

Agent 每次生成周报前，**并行尝试 fetch 本文件所有 URL**。对每个源：
- ✅ **fetch 成功** → 抽取信息，用于本次周报的模型推荐/合规判断
- ⚠️ **fetch 失败**（网络、认证、404 等）→ 不阻塞流程，跳过该源

无论成功失败，都在 brief.json 的 `canonical` 段（**顶层数组，不是 `coverage`**）追加一条记录，比如：
```json
{"label": "Azure 退役日历", "status": "found", "n": 1, "note": null}
{"label": "联想 AI 白名单", "status": "skipped", "n": 0,
 "note": "URL 需要联想 SSO；当前 agent 无认证工具。用户可通过 (a) SharePoint MCP (b) 浏览器下载后手动提供内容 来启用此源"}
```

### 2. 交叉验证（cross-check）

对每个项目 `current_stack` 里的每个模型，**两条并行的检查**：

**A. 退役日历检查**（用 Azure 那个）
- `Deprecated` / `Retired` → 生成 `退役预警` 卡片，`score: 10`（category=退役预警 会被 renderer 自动置顶为 urgent）
- 未来 6 个月内 EOL → 提前预警

**B. 白名单检查**（当白名单可读时）
- 在 Approved 列表 → 正常
- 在 Under Review 列表 → 在报告顶部"注意事项"区**黄色提示**"X 尚未正式批准"
- 完全不在白名单 → 在报告顶部**黄色提示**"注意：X 未在公司 AI 白名单，可能存在合规风险，请与 AI 平台组确认"
- 在 Not Approved 列表 → 同上，措辞更明确

**白名单读不到时**：跳过 B 全部检查，只跑 A。在 coverage 里透明记录"白名单未读到，本期推荐可能包含未经组织批准的模型"。

### 3. 推荐时的双重过滤

Agent 写 `business_impact` / `action_items` 时，**推荐替代模型必须同时满足**：
1. 官方（Azure/OpenAI/等）推荐路径
2. 在联想白名单 Approved 列表（**当白名单可读时**）

**如果白名单不可读**：只按第 1 条推荐，并在 tech_detail 里明确写"本推荐未与公司白名单交叉验证"。

**如果白名单可读但推荐目标不在其中**：说清"官方推荐 X，但 X 尚未列入公司白名单，需先申请审批。当前白名单内的 Y 也是备选"。

### 4. 用户追加自己的源

用户可以在本文件"三、用户追加区"里加自己关心的 URL。agent 会一视同仁地尝试 fetch，读不到就跳。
