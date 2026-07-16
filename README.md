# ai-brief

**给任意 agent（Claude Code / Codex / Hermes / …）配上"项目感知的 AI 情报简报"能力的工具包**（默认 30 天窗；周报 / 自定义起止见 [`SKILL.md`](SKILL.md) §1）。

你带着自己的 agent 和 API key；这个仓库负责确定性的活（解析文档、渲染 HTML）；你的 agent 负责创造性的活（搜集 AI 情报、判断相关性、写出对每个项目的影响）。

---

## 最简用法（配好之后，就一句话）

对你的 agent 说：

> **读 `AI_BRIEF/SKILL.md`，按里面的流程给 `<项目路径>` 生成本期 AI 情报。**

例如：

> 读 AI_BRIEF/SKILL.md，按里面的流程给 ./projects/acme-support 生成本期 AI 情报。

**这一句话足够了。** 所有硬约束都烧在 SKILL.md 里，agent 会自动遵守：

- 不许编造 URL / 模型名 / 日期
- 不许跨生态推荐 / 不许降级
- 面向 HR 业务读者的写作口吻
- canonical-sources 只是 baseline，8 维度矩阵自由搜索
- Step 4 打分批处理 (batch=3) + 落盘 `work/scored.json`，防 timeout
- 断了能续跑（见 SKILL.md §4.6）

产物在 `output/ai_brief_<项目slug>_<结束日期>.html`。

首次使用（还没装依赖 / 没配 MCP）继续往下读。

---

## 你需要什么

1. **一个你日常在用的 agent**（Claude Code、Codex CLI、Hermes 或任何能读文件+搜索+跑 shell 的 agent），配好自己的 API key
2. **一到多个项目输入**——可以是：
   - **本地文件夹**（含 `.pptx`/`.pdf`/`.xlsx`/`.docx`/`.md`/`.txt`）
   - **公开 URL**（arXiv、blog、GitHub README、公开新闻页）
   - **两者混合**（本地为主 + URL 补充）
3. 想追踪对这些项目"有影响"的 AI 动态

## 3 步上手

```bash
# 1) clone
git clone <this-repo> ai-brief
cd ai-brief
pip install -r requirements.txt

# 2) 让你的 agent 读 SKILL.md
# Claude Code:  会自动识别 SKILL.md
# Codex/其他:   把 SKILL.md 内容贴到系统提示，或让 agent 直接 read

# 3) 对 agent 说
"用 ai-brief 给这几个项目生成本期 AI 情报：~/projects/acme-support ~/projects/onboarding-bsr"

# 或者混合项目（本地 + URL）
"这里是 spec 文件 projects.spec.json，帮我生成本期 AI 情报"
```

agent 会按 [`SKILL.md`](SKILL.md) 里的 5 步流程执行。产物在 `output/ai_brief_<项目slug>_<结束日期>.html`。

## 输入方式

### 方式 A · 本地文件夹（最简单）
```bash
python tools/parse_docs.py ./projects/acme-support ./projects/onboarding-bsr --output work/parsed.json
```
每个文件夹 = 一个项目，id 自动从文件夹名生成。

### 方式 B · 混合（本地 + 公开 URL）
写一份 `projects.spec.json`（见 [`examples/projects.spec.example.json`](examples/projects.spec.example.json)）：
```json
{
  "projects": [
    {"id": "acme-support", "name": "Acme Support Assistant",
     "inputs": ["./projects/acme-support", "https://arxiv.org/abs/2606.12345"]},
    {"id": "onboarding", "name": "Onboarding BSR",
     "inputs": ["https://acme.com/onboarding-launch"]}
  ]
}
```
```bash
python tools/parse_docs.py --spec projects.spec.json --output work/parsed.json
```

### 方式 C · 认证 URL（SharePoint / Confluence / Notion / 飞书 …）
公开网页 agent 自己能拿；**认证网页 parse_docs 不直接支持**（会返回 `auth_required`）。按你 agent 的能力选：

| 方案 | 适合谁 | 用户动作 |
|---|---|---|
| **Agent 自带认证访问** | agent 挂了 SharePoint MCP / Confluence MCP / Notion MCP | 不用管，agent 用 MCP 下载到 `./work/downloads/<项目>/`，把该目录作为 folder 输入 |
| **下载到本地** | 一次性、图省事 | 从浏览器下载文档，扔到本地文件夹里，告诉 agent 路径 |

agent 看到 `auth_required` 会主动问你走哪条。**不会伪造内容**。

## 想要更丰富的情报来源？挂载搜索 MCP

Agent 默认能力有差异：Claude Code 内置的 WebSearch 仅限美国、以英文为主；有些环境（沙箱/内网）甚至完全没网。想让报告覆盖更全面（arxiv、Anthropic/OpenAI 博客、中文 AI 媒体、行业报告等），**强烈推荐在你的 agent 里挂一个 web search MCP**。

我们提供了配置样板 [`examples/mcp.example.json`](examples/mcp.example.json)，覆盖常用选项：

| MCP | 是否要 API key | 特点 |
|---|---|---|
| **fetch**（官方 Anthropic）| 免费无 key | 抓任意公开 URL 正文，比内置 WebFetch 少限制 |
| **brave-search** | 需要（免费额度大）| 通用网页搜索，质量稳定 |
| **tavily** | 需要（每月 1000 次免费）| AI-native，返回结构化答案，适合新闻聚合 |
| **exa** | 需要（有免费额度）| 语义搜索、找相似页面 |

把 `examples/mcp.example.json` 里对应的 `mcpServers` 条目合并到你 Claude Code 的 `~/.claude/settings.json`（或 Codex/其他 agent 的 MCP 配置），填入 API key，restart agent，就能显著提升 agent 的信息获取能力。

**产品行为**：SKILL.md 会告诉 agent 优先用 MCP，回退到内置 WebSearch，都不通就停下告知用户（**不会编造 URL**）。

## 项目材料 = 唯一偏好来源

工具不维护单独的 `preferences.md`。你希望报告按 GPT 生态推荐？在项目材料里说清"当前使用 GPT-4o / OpenAI"就行，agent 会自动同生态优先，且报告里每条推荐末尾都会小字标注 *依据：<项目文档>#<页码>*。

对某条推荐不满意？跟 agent 说话就行，两种模式（详见 [`SKILL.md`](SKILL.md) §5）：

- **调语气 / 侧重 / 白话度**（不动来源） — 例："第 3 条对咱们不算重点，写淡一点" / "讲得再白话点"。agent 只改这张卡片的文字，URL 保留，不会重跑整份报告。
- **换推荐目标 / 换更贴合的原始新闻**（会做窄搜索） — 例："把推荐从 GPT-5 改成 GPT-5.5" / "换一条更相关的原始新闻" / "别用 GPT 用 Qwen"。agent 会围绕新目标做一次窄搜索、覆盖这张卡片的 `url / title / summary` 和 `business_impact`，让链接和推荐重新对得上（点进去不会串味）。跑完会告诉你 "链接从 `<old>` 换成 `<new>`，因为 …"。

话说得不清楚（例："这条重写下"）agent 会反问你走哪种，不会默认乱搜也不会默认不改。想让偏好长期生效？更新对应项目文件夹里的材料，下次自动生效。

## 多项目

`ai-brief` 支持多项目一次性合并成 1 份报告：
- 报告顶部展示所有项目卡片（含技术栈）
- 每条动态一张卡片，展开显示对**每个相关项目**的独立影响列
- 与项目无关的项目栏自动隐藏

## 断点续传保证

Agent 是非确定性的执行者，可能 timeout、rate-limit、上下文溢出、被 API 限速踢下线。这个工具包的整条 pipeline **每一步都强制落盘到 `work/` 下的固定文件**——所以中断了不用重头来：

- Agent 崩了或被打断？让它跑同样的命令，它会扫 `work/` 找到断点，从缺的第一步续跑，之前完成的活直接复用
- Step 4（打分 + 写业务影响）是过往最容易崩的环节 → 强制约束**每处理完 3 条 candidate 就覆盖写一次** `work/scored.json`，即便打到一半崩了也只丢最多 2 条
- 所有中间产物 UTF-8 + `indent=2`，人类可读、可 `diff`、可手动 patch 后重跑
- 落盘用原子写（`.tmp` → rename），不会因中断产生半写坏 JSON

完整判定阶梯见 [`SKILL.md`](SKILL.md) §4.5 / §4.6。

## 目录

```
ai-brief/
├── README.md                   # 你在读的这份
├── SKILL.md                    # 给 agent 的完整流程（agent 会读这个）
├── requirements.txt            # jinja2, python-pptx, pypdf, openpyxl, python-docx, beautifulsoup4
├── tools/
│   ├── parse_docs.py           # CLI: 解析项目文件夹/URL → JSON
│   ├── verify_sources.py       # CLI: HEAD-check 每条 URL，标 link_status
│   ├── validate_brief.py       # CLI: 校验 brief.json
│   ├── render_report.py        # CLI: brief.json → HTML
│   └── finalize.py             # CLI: 一条命令跑 verify+validate+render
├── schema/
│   └── brief.schema.json       # 中间格式 JSON Schema
├── templates/
│   └── report.html             # FT 风格报告模板（暖米黄 + 衬线大标题）
├── references/
│   ├── canonical-sources.md    # 强制检索源清单（退役日历、白名单等，SKILL.md §3.1）
│   └── whitelist-rules.md      # 组织白名单 × 项目栈交叉验证规则（SKILL.md §3.1 Step C）
├── examples/
│   ├── brief.example.json      # 完整 brief.json 示例（不知道怎么写时对照它）
│   ├── mcp.example.json        # 推荐挂载的搜索 MCP 配置样板
│   └── projects.spec.example.json  # 混合本地文件夹 + URL 的输入规格样板
└── output/                     # 生成的 HTML 落在这里
```

## 试运行工具包本身（不用 agent）

```bash
pip install -r requirements.txt
python tools/render_report.py examples/brief.example.json
# → output/ai_brief_<slug>_2026-07-13.html，浏览器打开看效果
```

## 支持的输入格式

`.pptx` · `.pdf` · `.xlsx` / `.xls` · `.docx` · `.md` · `.txt`
