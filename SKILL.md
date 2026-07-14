# ai-brief — SKILL for AI Agents

> **You are an agent. This file tells you how to use the `ai-brief` toolkit to generate a project-aware AI weekly/monthly brief for the user.**
> The toolkit provides deterministic CLIs (doc parsing, URL verification, HTML rendering). Everything else — understanding the projects, searching AI news, judging relevance, writing per-project impact — is **your** job.

---

## 1 · What the user gives you

- One or more **project folders**. Each folder contains materials (`.pptx`, `.pdf`, `.xlsx`, `.docx`, `.md`, `.txt`) describing that project.
- Optionally a period (default: last 7 days = weekly).

## 2 · Golden Rules — read every run

### 2.1 Never invent, always cite

- **URLs cannot come from memory.** You cite only URLs you actually retrieved via a search or fetch tool in THIS session.
- **Model names, dates, statistics cannot come from memory.** If your training data suggests something, treat it as a hypothesis you must verify against a real source in this run.
- **If your search/browse tools are unavailable** (e.g. sandboxed, blocked, or offline), you MUST stop and tell the user: *"I can't reach the network to fetch real news right now. Please retry in a session where WebSearch/fetch is available."* Do NOT fabricate content to fill the brief.

### 2.2 Ecosystem lock-in

Every recommendation must respect the project's current stack.
- Project uses **GPT-4o** → recommend GPT-4.1 / GPT-5.x / o3-o4 series. Only cross to Claude/Qwen if user explicitly asks or the same-vendor path is dead (rare — even then flag it).
- Project uses **Qwen-3.5** → recommend Qwen-3.5-Max / Qwen-4 / Qwen-VL. Do NOT downgrade to Qwen-3.
- Project uses **Claude on AWS Bedrock** → recommend Anthropic + AWS solutions.
- Project uses different stacks per region (e.g. China Qwen-3.5, Overseas GPT-4o) → give **per-region** analysis.
- If the docs don't say what stack is used → stay neutral, list mainstream options, mark `same_ecosystem: null`.

**Downgrade rule**: never recommend a version older than what the project currently runs. Qwen-3 for a Qwen-3.5 user is a downgrade — flag as an error.

### 2.3 Business-first writing (users are HR / business owners, not engineers)

- Write in first-person Chinese ("咱们…", "我们的员工…") — sound like an internal colleague, not a report.
- Avoid jargon. If you must use a technical term, add a short parenthetical explanation.
- Every `impact` MUST be split into three plain-language fields (see §5 impact schema).
- Every `action_items` entry ≤ 20 characters, imperative verb first ("本月内启动兼容测试", not "考虑评估一下兼容性方面的工作").
- Put engineering-level nuance into `tech_detail` — the HTML folds it under a click-to-expand.

---

## 3 · Mandatory pre-checks BEFORE writing any recommendation

### 3.1 强制源清单（canonical floor — 拉 + 交叉检查）

> **canonical-sources.md 是 FLOOR，不是 CEILING.** 这些 URL 是不可跳过的底线（比如 Azure 退役日历——漏掉 = GPT-4o EOL 没预警 = 周报报废）。但它们只覆盖 §3.2 里 8 维度中 A 维度的**一部分**。B-H 你必须自己跑（见 §3.2）。**如果周报里只引用了 canonical URL，你就失败了 §3.2**。

**Step A — 拉取每一条 canonical URL（并行）**

1. 读 `references/canonical-sources.md`，把里面**每一条** URL 并行 fetch。不许因为"我觉得需要认证"就跳——先真的试一次，再处理结果。
2. 每一条的结果落到 `brief.json` 顶层的 `canonical: []` 数组（**注意：不是 `coverage`**）：
   ```json
   "canonical": [
     {"label": "Azure 退役日历", "status": "found", "n": 1, "note": null},
     {"label": "联想 AI 白名单", "status": "skipped", "n": 0,
      "note": "URL 需要联想 SSO；当前 agent 无认证工具。用户可通过 SharePoint MCP / 手动下载 启用此源"}
   ]
   ```
3. Read-failures **不是错误**——认证源在没配 MCP 时预期会 fail。不要重试、不要伪造内容、不要阻塞流程。
4. `status` 取值：`found | empty | skipped | error`。任何非 found 状态必须写 `note` 解释。

**Step B — 退役日历 × 项目栈（自动交叉检查）**

canonical 拉到退役日历后，对每个项目 `current_stack` 里的每个模型：
- **Deprecated / Retired** → 生成 `退役预警` 文章，`score: 10`（category=退役预警 会被 renderer 自动标记为 urgent）
- **GA but retirement date within 6 months** → early warning card
- Azure 的 `Replacement` 列直接写进 `business_impact` 和 `action_items`

例子：日历显示 GPT-4o 2026-10-01 停用，替代 gpt-5.1，项目用 GPT-4o → 必须出现退役预警。

**Step C — 白名单 × 项目栈（当白名单可读时）**

**当组织白名单成功拉到**（canonical 里对应条目 status="found"）：

对每个 stack 模型交叉检查：

| stack 模型状态 | agent 处理 |
|---|---|
| ✅ Approved | 正常，无需提示 |
| 🟡 Under Review | 报告顶部**注意事项**黄色提示："X 尚未正式批准，请与 AI 平台组确认" |
| ⚠️ 不在白名单 | "X 未在公司 AI 白名单，可能存在合规风险" |
| ❌ Not Approved | "X 未获批准使用，请立即评估切换"（措辞更明确） |

**这是 soft warning**（提醒但不紧急），不 urgent/红。合规不匹配对用户重要，但周报里通常不算 red-alert。

**推荐双过滤**：
- 任何在 `business_impact` / `action_items` / `tech_detail` 里当建议提出来的模型名必须在 Approved 名单内
- 若 Azure 推荐 X 作为退役替代但 X 不在白名单 → 两句都写："官方推荐 X（尚未列入公司白名单，需先申请审批），当前白名单内的替代方案是 Y"

**当白名单未读到**（status != "found"）：

- 跳过 Step C
- 报告顶部 `notices` 里加一条："本期公司 AI 白名单未读到（<原因>），推荐模型未与公司白名单交叉验证。用户 agent 若有相应能力（SharePoint MCP / 手动提供内容），可获得更精确的合规过滤"
- 其他一切照常。

### 3.2 8 维度自由检索 — 别让一个维度独霸

**A project-aware brief is not "AI news around the project's tech stack".** It is **"any AI-adjacent signal that affects the project's ability to deliver its business goal"**. Model news is only ONE of the following dimensions. You MUST attempt at least 5 of them per run:

| # | Dimension | What to search for | Example queries for an HR agent project |
|---|---|---|---|
| A | **模型 & 平台** | new model releases, retirements, pricing, capability upgrades affecting the project's stack | "GPT-5.1 release notes", "Qwen 3.5 update", "Bedrock new feature" |
| B | **行业监管 & 合规** | AI Act, GDPR, PIPL, industry-specific labor law, employee data rules | "EU AI Act HR high-risk", "PIPL 员工数据 AI", "AI hiring bias regulation" |
| C | **同行案例 & 落地** | how competitors / peers in the same industry deploy similar AI | "Fortune 500 HR chatbot case", "员工服务 AI 大厂落地", "IBM HR bot" |
| D | **学术进展** | recent arXiv / NeurIPS / ACL / EMNLP papers directly matching project's technical focus | "arXiv dialogue state tracking 2026", "multi-agent routing survey" |
| E | **开源工具 & 框架** | new libraries/frameworks that could replace or enhance the project's tech | "LangGraph 1.0", "AutoGen enterprise", "dspy update" |
| F | **厂商产品动态** | vendor-specific launches (SaaS product news relevant to the project's domain) | "Workday AI feature", "SAP SuccessFactors AI", "北森 AI 招聘" |
| G | **行业报告 & 观点** | analyst / thought-leader pieces about the project's business domain × AI | "Gartner HR AI report", "麦肯锡 HR AI 2026" |
| H | **安全 & 事件** | breaches, misuse cases, AI incidents in the project's domain | "HR chatbot data leak", "AI hiring discrimination lawsuit" |

**How to pick which 5+ dimensions**: read the project docs, then choose the dimensions that would matter most to a BUSINESS OWNER of that project. For an HR agent project:
- A, B, C, F, G are usually mandatory (models, regulation, peer cases, HR-vendor products, industry reports).
- D, E, H are strongly recommended.

**Per-dimension coverage log** — 顶层的 `coverage: []` 数组（**注意：与 §3.1 的 `canonical: []` 分开**），只允许 A–H 单字母 `dim`：

```json
"coverage": [
  {"dim": "A", "label": "模型 & 平台",     "status": "found", "n": 3, "note": null},
  {"dim": "B", "label": "行业监管 & 合规", "status": "found", "n": 2, "note": null},
  {"dim": "C", "label": "同行案例 & 落地", "status": "found", "n": 1, "note": null},
  {"dim": "D", "label": "学术进展",       "status": "empty", "n": 0,
    "note": "本期 arXiv 未发现直接对齐 slide-6 Query Rewrite 的新论文"},
  {"dim": "F", "label": "厂商产品动态",   "status": "found", "n": 2, "note": null}
]
```

The HTML template renders `canonical` 和 `coverage` 分成两栏在诊断区，用户一眼看到哪些维度来空，就知道你不是懒。

**Status values**: `found` (≥1 article included), `empty` (searched but no relevant result), `skipped` (deliberately not searched — must explain why in `note`).

**允许合并相邻维度检索**：如果两个维度的关键词高度重叠（例如 C 同行案例 + F 厂商产品动态），可以做一次合并查询以省 token / API 调用。此时 `coverage` 必须两条都记录：主的一条按 `found n=X` 记，被合并的一条按 `found n=0` + `note: "并入 <主维度>"` 记，保持诊断表格完整。绝不允许「合并了就只记一条」，用户会以为你漏搜了。

**Anti-pattern to avoid**: last run I only fetched the Azure retirement calendar because it was in my allowlist, so all 3 articles were about model retirements. That is NOT a project-aware brief — that is a model-vendor bulletin. If your search tool succeeds on some domains and fails on others, do NOT let the successful domain dominate the brief. Log the failures in `coverage[].note` and tell the user how to unblock those sources next time.

---

## 4 · The 5-step workflow

### Step 1 — Parse project docs (local folders + URLs)

The user may give you:
- **Folder paths** (each folder = one project, id = slugified folder name)
- **Public URLs** (arXiv, blog posts, GitHub READMEs, etc. — fetchable without auth)
- **Authenticated URLs** (SharePoint, Confluence, Notion, Google Docs, 飞书, etc. — cannot be fetched by parse_docs directly)

**Two invocation modes:**

```bash
# Mode 1: folder-only (backward-compat)
python tools/parse_docs.py <folder1> [<folder2> ...] --output work/parsed.json

# Mode 2: mixed folders + public URLs via JSON spec (see examples/projects.spec.example.json)
python tools/parse_docs.py --spec work/projects.spec.json --output work/parsed.json
```

**When to build a spec file**: any time the user mentions URLs or has mixed input. Structure:

```json
{
  "projects": [
    {"id": "acme-support", "name": "Acme Support Assistant",
     "inputs": ["./projects/acme-support", "https://arxiv.org/abs/2606.12345"]},
    {"id": "onboarding", "name": "Onboarding BSR",
     "inputs": ["./work/downloads/onboarding-bsr"]}
  ]
}
```

Rules:
- `id` is required; kebab_case; must match what you use as key in article impacts.
- `name` is required when `inputs` are all URLs (no folder to infer from).
- Each input is a string — either a filesystem path or `http(s)://` URL.

**Handling auth-required URLs** (SharePoint, Confluence, Notion, Google Docs, 飞书, Lark, Office 365):

`parse_docs.py` does NOT support cookie bridges or session auth. Any authenticated URL will come back as `status: "auth_required"`. When you see this, pick one of two paths:

**Option A · You have authenticated MCP access** (SharePoint MCP / Confluence MCP / Notion MCP / any authenticated fetch tool): use your MCP to download the content, save it to `./work/downloads/<project-id>/` (as `.md`, `.html`, `.pptx`, `.pdf` etc.), then include that directory as a folder input in the spec.

**Option B · Ask the user to download**: if you have no authenticated access, tell the user:

```
"检测到 URL 需要认证：<url>
 我在当前会话中没有该域名的认证凭证。你有两种选择：
 (a) 你在浏览器里点下载，把文件放到本地文件夹，告诉我路径；
 (b) 如果你的 agent 支持相应 MCP（SharePoint / Confluence / Notion 等），先挂上再重跑，
     我会用它下载到 ./work/downloads/ 然后当作 folder 输入。
 你希望走哪条？"
```

**Only skip a source if the user explicitly says "skip it".** Log the skip in `canonical[].note` or `coverage[].note`.

**Never fabricate content when a URL fails.** Missing sources should result in fewer articles or an `empty` coverage cell — not made-up bullshit.

### Step 2 — Understand each project

For each project in `parsed.json`, read `files[].text` and produce:
- `summary`: 3–5 sentences (Chinese)
- `domain`
- `current_stack`:
  - `models`, `vendors`, `frameworks`: extracted from docs
  - `regions`: use array like `["中国区：Qwen-3.5", "海外区：GPT-4o"]` when different regions use different stacks
  - `sources`: doc citations
  - **If a project has a `stack.md`, prioritize it** — that's the user's declared source of truth.
  - If neither the general docs nor `stack.md` specify → omit `current_stack` entirely.
- `keywords`: 5–10 specific search terms

**Fixed output file** — write the resulting per-project info to `work/project_info.json`:
```json
{
  "projects": {
    "<project-id>": {"summary": "...", "domain": "...", "current_stack": {...}, "keywords": [...]}
  }
}
```

### Step 3 — Fetch canonical sources FIRST, then search

**In this exact order:**

1. Fetch every URL in `references/canonical-sources.md` (retirement calendars, vendor deprecation pages).
2. Cross-check each project's `current_stack` models against those calendars. Any hits → seed `articles` with `退役预警` cards (category=退役预警 会被 renderer 自动置顶为 urgent；见 §3.1 Step B / Step 4)。
3. THEN use your search/browsing tools to look for the last N days of AI news relevant to each project's `keywords`.

**Search tool priority — use the strongest one available**:
- If MCP servers are configured (Brave Search / Tavily / Exa / official fetch) → **strongly prefer** these over the built-in WebSearch. They tend to have wider coverage, more current results, and less regional restriction (built-in WebSearch is US-only + English-first).
- If no MCP → fall back to built-in `WebSearch` + `WebFetch`.
- If BOTH fail (sandboxed session, network blocked) → follow the "cannot fetch" rule in §2.1 — stop and tell the user, do not fabricate.

**Recommended MCPs for the user to install** (in `.mcp.json` or Claude Code settings, see `examples/mcp.example.json`):
- **brave-search** — high-quality general web search, generous free tier
- **tavily** — AI-native structured search, best for news synthesis
- **exa** — semantic / "find similar" search, great for research
- **fetch** — official Anthropic MCP fetch, gets past many WebFetch restrictions

If you notice all sources this run come from ONE domain (e.g. only Wikipedia), that's a strong signal your search tools are restricted. Log this in `coverage[].note` so the user knows to enable an MCP.

**Source diversity target** (per SKILL.md §3.2):
- Aim for **20–40 candidate items** total across all projects
- Prefer: vendor blogs (OpenAI, Anthropic, Google DeepMind, Meta AI, AWS, Azure, 阿里云通义, 智谱, DeepSeek), Chinese AI media (机器之心, 量子位, 36氪 AI, PaperWeekly), arXiv (cs.CL/cs.AI/cs.LG), tech news (Hacker News, TechCrunch, MIT Tech Review), analyst blogs (Gartner, McKinsey, a16z, Sequoia)
- **Do NOT accept a report where 3+ articles come from a single Wikipedia page** — that's a red flag your search is broken

For each candidate, record: `title`, `url`, `source`, `published (YYYY-MM-DD)`, `lang (cn|en)`, and 2–4 sentence `summary`.

**Fixed output files** — write each dimension's raw hits and an aggregated de-duped candidate list:
- `work/searches/dim_<letter>.json` — one file per dimension attempted (e.g. `dim_A.json`, `dim_B.json`, ...)
- `work/candidates.json` — aggregated, de-duped candidate list ready for Step 4

### Step 4 — Judge & write per-project impact

⚠️ **韧性硬约束（本步是过往 timeout / rate-limit 最集中的环节，必须批处理落盘）**：

- **每处理完 3 条候选，就把当前累积的 scored 列表覆盖写到 `work/scored.json`**（不是追加、不是攒到最后一次性写）。
- 覆盖写用**原子写**：先写 `work/scored.json.tmp`，再 `rename` 到最终路径，防止半写文件让下次 resume 读到坏 JSON。
- 候选数是 5 条还是 500 条都这么走。`batch=3` **不可调**——过往实测超过 3 条就容易触发 timeout 或上下文溢出，这是产品级默认。
- 打到一半崩了也没关系：下次 resume 从 `candidates.json` 里未在 `scored.json` 出现的第一条继续（见 §4.6）。

For each candidate article, decide:

1. **`category`**: `模型发布 | 论文 | 工具 | 政策 | 应用 | 观点 | 退役预警`
   - `退役预警` 会被 renderer 自动置顶为 urgent（红色 badge、TL;DR 顶部），你**不需要**单独写 `urgent` 字段。
2. **`score`** (0–10) overall relevance to at least one project:
   - 10: directly affects a project's stack/roadmap NOW (EOL warnings, drop-in replacements)
   - 7–9: relevant tech/method worth referencing
   - 4–6: domain-adjacent, indirect
   - < 4: skip
3. **`impacts`**: keyed by project id, value is `null` (irrelevant) or:
   ```
   {
     "what_happened":    "1 sentence, plain Chinese, what the news is",
     "business_impact":  "2-4 sentences, first-person '咱们…', concrete impact on THIS project",
     "action_items":     ["≤ 20-char imperative action", "..."],
     "tech_detail":      "optional engineering notes, folded in HTML",
     "grounded_on":      "cite project doc, e.g. 'stack.md（海外区当前用 GPT-4o）'",
     "same_ecosystem":   true | false | null
   }
   ```

Enforce §2.2 (ecosystem lock-in) and §2.3 (business language) at this step.

Only keep articles with score ≥ 6 for at least one project.

### Step 5 — Verify, validate, render

组装完 `work/brief.json` 后，一条命令收尾：

```bash
python tools/finalize.py work/brief.json
# 内部依次跑 verify_sources → validate_brief → render_report
# 任一失败早退。输出到 output/ai_brief_<slug>_<end-date>.html
```

如果需要单独跑某一步（进阶用户）：

```bash
python tools/verify_sources.py work/brief.json     # HEAD-check every URL, sets link_status
python tools/validate_brief.py work/brief.json     # Schema check
python tools/render_report.py work/brief.json      # → output/ai_brief_<slug>_<end-date>.html
```

If `verify_sources.py` reports any `broken` URLs:
- If it's a URL you fabricated → replace it with a real one from your search results, or drop the article.
- If it's a temporary outage of a real URL → keep it. The HTML shows a red `⚠️ 链接不可达` badge automatically.

Tell the user the output path when done.

---

### 4.5 · 中间产物落盘（韧性保障）

**每一步都必须把产物写到 `work/` 下的固定路径**。这不是可选建议——是让整条 pipeline 在 timeout / rate-limit / 会话崩溃后可 resume 的**唯一机制**。

| 步骤 | 落盘路径 | 何时写 |
|---|---|---|
| Step 1 Parse | `work/parsed.json` | 每次运行覆盖写 |
| Step 2 Understand | `work/project_info.json` | 生成完 summary + current_stack + keywords 后写一次 |
| Step 3.1 Canonical | `work/canonical.json` | 每 canonical URL fetch 结果都落一条（成功/失败都记，含抽取到的关键行） |
| Step 3.2 Searches | `work/searches/dim_<X>.json` | 每 dim 检索完立即写自己那份，一个 dim 一个文件 |
| Step 3.3 Dedup | `work/candidates.json` | dedup 完写一次 |
| Step 4 Judge | `work/scored.json` | **每处理完 3 条 candidate 就覆盖写一次**（见 Step 4 硬约束） |
| Step 5 Assemble | `work/brief.json` | 组装完写一次；HTML 由 render 单独产出到 `output/` |

**通用规则**（对所有中间文件都适用）：

- **覆盖写而不是追加**——JSON 追加会破坏结构，也做不到 partial recovery。
- **原子写**：先写 `<path>.tmp` 再 `rename` 到最终路径。中断在 rename 之前——正式文件仍是上次的完整版本；中断在 rename 之后——新版本已完整落盘。任一情况都不会出坏 JSON。
- **中间文件都要 self-describing**：`candidates.json` 里每条至少要有 `id / dim / url / title / summary_cn / published / source`，让下游步骤不用回头翻 `dim_*.json` 就能理解。同理 `scored.json` 每条要包含原 candidate 的所有字段 + `score / category / urgent / impacts`。
- **UTF-8 + `indent=2`**：所有中间文件人类可读、可 `diff`、可手动 patch 后重跑。

### 4.6 · Resume · 断点续传

当用户说「接着 XX 项目续跑」/「continue the last brief」/「从上次断点继续」这类意思时：

**不要重头开始**。扫 `work/` 判定阶段，从缺的最早那一步开始接着跑，之前的产物直接读取复用。

**判定阶梯**（自上而下依次检查，命中第一条就从那开始）：

| 现有产物状态 | 从哪续 |
|---|---|
| 无 `work/parsed.json` | Step 1 Parse |
| 有 parsed / 无 `work/project_info.json` | Step 2 Understand |
| 有 project_info / 无 `work/canonical.json` | Step 3.1 Canonical fetch |
| 有 canonical / `work/searches/` 里应有的 dim 不全 | 只补缺的 `dim_<X>.json` |
| 有 searches 全 / 无 `work/candidates.json` | Step 3.3 Dedup |
| 有 candidates / `scored.json` 条数 < candidates 条数 | 从未打分的第一条继续（**上次超时最常见的场景**） |
| 有 candidates / 无 `scored.json` | Step 4 Judge 从头 |
| scored 满 / 无 `work/brief.json` | Step 5 Assemble |
| 有 `work/brief.json` / 无 HTML | 直接 `python tools/finalize.py work/brief.json` |

**Resume 时告诉用户你在哪里接**（一句话即可）：「检测到 X/Y 条已打分，从第 X+1 条继续」。让用户看得见状态，不是黑盒。

**边缘情况**：

- `scored.json` 里的某条 `id` 在 `candidates.json` 里找不到 → 用户可能手动改过 candidates；干净重跑 Step 4。
- `parsed.json` 里的项目和 `project_info.json` 里的不匹配 → 用户可能换了输入；从 Step 2 重跑。
- 发现 `<path>.tmp` 残留文件 → 上次中断在原子写之前；删掉 `.tmp`，从对应正式文件开始判定。
- 用户明确说「不要 resume，从头重跑」→ 清空 `work/` 后正常走 Step 1。

---

## 5 · Handling user feedback

**Localized patch** — user says "把第 3 条对 acme-support 的建议改成 GPT-5.5":
1. Open `work/brief.json`, find the article, edit `impacts.acme-support.business_impact` / `action_items` / `tech_detail`.
2. Do NOT re-search, do NOT touch other cards.
3. Re-run `verify_sources.py` + `validate_brief.py` + `render_report.py`.

**Persistent preference** — user says "以后都推 GPT 系":
1. Do NOT create a separate preferences file.
2. Suggest updating the project's `stack.md` with something like:
   ```
   # <项目> 当前技术栈
   - 中国区：Qwen-3.5-Max（阿里云 DashScope）
   - 海外区：GPT-4o（Azure OpenAI）
   - 部署：私有云 + Azure OpenAI
   ```
3. Next run reads it automatically.

**Too technical** — user says "把第 N 条讲得再白话点":
1. Rewrite `business_impact` and `action_items` in plainer Chinese.
2. Move technical nuance into `tech_detail`.
3. Re-render.

---

## 6 · Multi-project reports

Rule: **one merged brief per run**.
- All projects appear in the top project wall.
- Each article appears once, with per-project impact panels — some may be `null` (that panel just doesn't render).
- Only include an article if at least one project has non-null impact and score ≥ 6.

---

## 7 · Absolute constraints

- Never invent facts, model names, URLs, statistics.
- Every URL must be verified by `verify_sources.py` (or manually checked by you) in the same run.
- `impacts` keys MUST match `projects[].id` exactly.
- `business_impact` must reference concrete elements of the project (a slide, a use case, a region, a stack item) — no generic "该动态可作为参考".
- Recommendations must respect ecosystem lock-in (§2.2). Downgrades are errors.
- If `stack.md` exists in a project folder, it overrides any inference from general docs.

Full JSON contract: [`schema/brief.schema.json`](schema/brief.schema.json).
Reference example: [`examples/brief.example.json`](examples/brief.example.json).
Canonical sources: [`references/canonical-sources.md`](references/canonical-sources.md).
