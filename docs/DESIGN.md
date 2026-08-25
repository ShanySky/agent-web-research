# 设计方案：Web Research Router + Exa Retrieval + web-searcher

## 1. 目标

构建一套长期可维护、尽量宿主无关的 Web Research 体系：

1. 主代理缺少宿主 Native Web Search 时仍可通过 Exa 检索；
2. 不需要全局常驻 Exa MCP schema；
3. Native Search 恢复后，Native 与 Exa 不会随机竞争；
4. 复杂检索由 `web-searcher` 隔离噪音；
5. 路由规则本身也 progressive disclosure；
6. 默认不强迫项目新增“规则目录”；
7. 可通过 Codex Plugin 分发，同时保留 Direct 安装与其它宿主迁移空间。

## 2. 非目标

- 不覆盖 Exa 所有历史/deprecated MCP 工具。
- 不为每一种网站、问题类型写微路由。
- 不追求每次猜到理论最优搜索引擎；优先稳定、可预测、可排错。
- 不让 Exa Agent 成为默认复杂研究路径。

## 3. 名称与职责

插件整体名称：`agent-web-research`。它描述的是整套 Agent Web Research 能力，不绑定 Exa，也不把核心设计限制为 Codex 专属。

```text
web-research-router = 两层路由 Skill；决定执行者与检索后端
web-searcher         = 执行复杂 Web Research 的子代理
exa-retrieval        = Exa 检索 Skill + Python CLI
Native Web Search    = 宿主提供的原生网页搜索/浏览能力
```

避免使用过泛的 `search-routing`，也避免自定义 Skill 使用 `web-search` 这种容易和宿主工具混淆的名称。

## 4. 两层 Router

### 第一层：Execution Router —— 谁来搜？

**主代理**：单点事实、少量文档/issue/release、低噪音、少量查询与来源即可确认。

**`web-searcher`**：多轮、多角度、多源核验、较多网页、社群/benchmark/竞品调查、或原始结果会明显污染主上下文。

关键规则：**不要仅因为主代理缺少 Native Search 就派子代理。先按工作量与噪音决定执行者。**

### 第二层：Retrieval Router —— 主代理用哪个后端？

**Native Web Search**：可用时，一般 Web、最新事实、浏览/导航、宿主原生页面交互默认优先。

**Exa Retrieval**：Native 不可用；语义/概念发现；长尾技术资料；GitHub/论文/开发者资料 discovery；严格 domain/date/category 过滤；或 Native 合理尝试后结果明显不足。

**Fallback**：只有首选结果明显不足才切另一后端；不要无目的双搜。

## 5. Router 为什么做成独立 Skill

默认不再要求：

```text
.agents/custom-rules/search-*.md
rules/search-*.md
```

而使用：

```text
web-research-router/SKILL.md
```

理由：

- 不强迫团队接受新的规则目录约定；
- Skill catalog 只暴露少量元数据，正文按需加载；
- 能与 `exa-retrieval` 一起通过 Plugin 分发；
- 路由 Skill 与 Exa Skill 职责分离：前者决定路径，后者只教“已经决定用 Exa 后怎么调用”；
- 核心语义不绑定 Codex，迁移其它 Agent 宿主时只需调整宿主适配层。

AGENTS 仍保留极薄 bootstrap，以避免“为了知道是否该加载 Router Skill，先得加载 Router Skill”的循环依赖。

## 6. 三种运行时接入

### 默认：Skill Router

```text
AGENTS thin bootstrap
      ↓ ambiguity / fallback / scope growth
web-research-router Skill
      ↓
executor + backend choice
```

不创建规则目录。

### Inline

完整两层路由直接放 AGENTS；固定上下文略高，但最自足。

### File（兼容/偏好）

AGENTS 薄引用 + `web-research-router.md`。只有已有规则目录文化的团队才推荐使用，路径由 `--rules-dir` 指定。

## 7. 当前 Codex 集成示例

当前常见状态：主代理 custom GPT-5.6 无 Native，而 `web-searcher` GPT-5.4 有 Native：

```text
简单/低噪音 -> Main -> Exa
复杂/高噪音 -> web-searcher -> Native
```

未来主代理 Native 恢复：

```text
简单一般 Web -> Main -> Native
简单语义/长尾/精确过滤 -> Main -> Exa
复杂调研 -> web-searcher -> 其可用后端
```

第一层规则不需要变化。

## 8. Exa 能力分层

Exa 当前核心 MCP 能力映射为：

| 层级 | CLI | 默认披露 | 目的 |
|---|---|---:|---|
| 常用 | `find` | 是 | Search + highlights |
| 常用 | `read` | 是 | 读取已知 URL |
| 高级 | `advanced` | 否 | 日期/域名/category/搜索模式等 |
| 研究 | `research` | 否 | Exa Agent，多步研究 |

Deprecated MCP tools 不进入新 contract。

## 9. 双 Transport：REST 主路径 + Hosted MCP 匿名 fallback

运行时不是把 Exa MCP 注册给宿主，而是：

```text
Agent shell -> Python CLI -> Transport Router
                         -> REST API（有 EXA_API_KEY，优先）
                         -> Hosted MCP（无 Key，或 REST 配额临时耗尽）
```

这样保留两个目标：

1. 模型上下文只需要学习少量 CLI contract，不长期携带 MCP tool schema；
2. 用户没有 Exa Key 时仍可立即使用基础检索。

### 9.1 为什么 REST 仍是有 Key 时的默认

REST 链路更短、JSON contract 更稳定、错误更直接；因此 `EXA_TRANSPORT=auto` 检测到 `EXA_API_KEY` 时优先 REST。

如果 REST 返回 Exa 官方定义的 402 配额/预算 tag（`NO_MORE_CREDITS`、`API_KEY_BUDGET_EXCEEDED`、`TEAM_BUDGET_EXCEEDED`），且该操作存在等价 Hosted MCP 能力，则临时切到**匿名 MCP**。429/401/403/5xx 不触发这一降级。降级状态默认保留 1 小时，到期自动 probe REST；probe 成功后清除状态并恢复 Key。显式 `EXA_TRANSPORT=api` 不做 fallback。

### 9.2 为什么匿名 MCP 不再每次 initialize

Exa Hosted MCP 当前实际协商 MCP `2025-11-25`，仍是 session-based Streamable HTTP；2026-08-19 的上游协议探测显示 `2026-07-28` 尚未被 hosted endpoint 接受。CLI 因此缓存 `Mcp-Session-Id` 跨进程复用，不调用 `tools/list`；只有首次、缓存超过 20 小时或 session 失效时才重新 initialize。匿名与认证 session 分开缓存；402 fallback 强制匿名，避免把已耗尽 Key 带入 Hosted MCP。Exa 当前客户端 metadata TTL 为 24 小时。

不引入 daemon：为节省一次握手而增加后台进程生命周期、端口、崩溃恢复和多项目并发复杂度，不符合本包轻量目标。

### 9.3 能力边界

- `find` / `read`：REST 或匿名 Hosted MCP。
- `advanced`：`auto/fast/instant` + 过滤可 MCP；deep 系列仅 REST + Key。
- `research`：Exa Agent REST，仅 Key。

未来 Exa 正式支持 MCP `2026-07-28` stateless 后，只替换 transport 层即可，Skill/Router/CLI contract 不变。

### 9.4 UTF-8 I/O 契约

字符编码由 CLI 自己负责，而不是交给宿主 shell 配置。REST/MCP 响应显式 UTF-8 解码，缓存文件显式 UTF-8，CLI 入口统一将 `stdout/stderr` 重配为 UTF-8。这样 Windows PowerShell/CMD 即使默认代码页为 GBK，也不应造成中文乱码或 `UnicodeEncodeError`。

## 10. Progressive disclosure

`exa-retrieval` 主 Skill 只教基础 `find/read` 与何时读取 advanced/research reference。

`web-research-router` 只在路由不清、需要 fallback、或任务范围明显扩大时加载。

因此运行时上下文由任务需求决定，而不是把完整工具和规则长期注入。

## 11. 可观测性

Exa CLI 输出保留：

```text
provider: exa
operation: find|read|advanced|research
transport: api|mcp
request_id: ...
cost_usd: ...   # API 返回时
mcp_session_reused: true|false   # MCP 时
fallback_reason: api_quota_exhausted|api_quota_exhausted_cached
api_quota_tag: ...
api_quota_recovered: true       # probe 成功并恢复 REST 时
```

`web-searcher` 返回实际使用的检索后端。用户发现搜索质量波动时能定位来源。

## 12. Plugin / Direct

### Plugin

Codex Plugin 提供：

```text
skills/web-research-router
skills/exa-retrieval
```

### Direct

项目直接安装：

```text
.agents/skills/web-research-router
.agents/skills/exa-retrieval
.codex/agents/web-searcher.toml
```

File routing 风格时才额外创建：

```text
<rules-dir>/web-research-router.md
```

Plugin 是方便分发层，不是唯一运行前提。

## 13. 安全与迁移

- `EXA_API_KEY` 缺失：基础能力自动使用 Hosted MCP；只有 API-only 能力明确报需要 Key。
- 429/5xx：有限重试，不无限循环。
- deep：显式 `--allow-deep`。
- Exa Agent 新 run：显式 `--confirm-cost`。
- 已有 Skill/rule：不静默覆盖，内容不同生成 candidate。
- 已有 `web-searcher.toml`：始终保留原文件并生成候选版本供合并。
- AGENTS patch 使用新 marker `web-research-router`，同时识别旧版 marker 并原位迁移。

## 14. 上游依据

核实日期：2026-08-25。

- Exa Search API: https://exa.ai/docs/reference/search
- Exa Contents API: https://exa.ai/docs/reference/get-contents
- Exa Agent: https://exa.ai/docs/reference/agent-api/create-a-run
- Exa MCP: https://github.com/exa-labs/exa-mcp-server
- OpenAI Codex Plugins: https://github.com/openai/plugins
- CodeAlive-AI/exa-skills: https://github.com/CodeAlive-AI/exa-skills
- HKUDS/CLI-Anything: https://github.com/HKUDS/CLI-Anything
