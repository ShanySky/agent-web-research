# 设计方案：Web Research Router + Exa Retrieval + Context7 Tech Docs + web-searcher

## 1. 目标

构建一套长期可维护、尽量宿主无关的 Research / Technical Docs 体系：

1. 主代理缺少宿主 Native Web Search 时仍可通过 Exa 检索；
2. 不需要全局常驻 Exa / Context7 MCP schema；
3. Native Search 恢复后，Native 与 Exa 不会随机竞争；
4. 复杂检索由 `web-searcher` 隔离噪音；
5. 版本敏感的第三方技术事实由 Context7 做按需校准；
6. 路由规则本身 progressive disclosure；
7. 默认不强迫项目新增“规则目录”；
8. 可通过 Codex Plugin 分发，同时保留 Direct 安装与其它宿主迁移空间。

## 2. 非目标

- 不覆盖 Exa 所有历史/deprecated MCP 工具。
- 不把 Context7 变成“逢库必查”的强制代理层。
- 不为每一种网站、问题类型写微路由。
- 不追求每次猜到理论最优搜索引擎；优先稳定、可预测、可排错。
- 不让 Exa Agent 成为默认复杂研究路径。
- 不自动修改业务项目的 Node 版本，也不强制安装 fnm。

## 3. 名称与职责

插件整体名称：`agent-web-research`。它描述的是整套 Agent Research 能力，不绑定 Exa，也不把核心设计限制为 Codex 专属。

```text
web-research-router = 路由 Skill；决定执行者与事实源
web-searcher         = 执行复杂 Web Research 的子代理
exa-retrieval        = Exa 检索 Skill + Python CLI
context7-tech-docs   = Context7 版本敏感技术文档校准 Skill
Native Web Search    = 宿主提供的原生网页搜索/浏览能力
ctx7                 = Context7 官方 CLI contract
```

避免使用过泛的 `search-routing`，也避免自定义 Skill 使用 `web-search` 这种容易和宿主工具混淆的名称。

## 4. 信息需求先分两类

### 4.1 版本敏感开发文档

以下问题优先考虑 Context7：

- Library / Framework / SDK / API / CLI 当前或指定版本用法；
- Configuration；
- Migration；
- deprecated / replaced API；
- 编码前对第三方框架当前行为的技术事实校准。

简单原则：

```text
“这个技术在当前/指定版本应该怎么正确使用？” → Context7
```

### 4.2 开放互联网 Research

以下问题继续进入 Web Research 路由：

- 最新 Release 动态；
- Bug / GitHub Issue；
- 社区评价；
- 博客、新闻；
- 项目/替代方案发现；
- 一般 Web 事实与时效信息。

简单原则：

```text
“外界最近关于这个技术发生了什么？” → Native / Exa / GitHub / web-searcher
```

Context7 不是 Web Search 的替代品，也不是独立搜索层的唯一入口。

## 5. Context7 的双入口

Context7 有两种触发方式：

1. **编码任务直接触发**：Agent 准备依据记忆编写版本敏感的第三方 API/配置，但存在真实不确定时，直接加载 `context7-tech-docs`；不要求先经过 Router。
2. **Router 边界路由**：当 Web Research/技术信息问题在事实源选择上不明确时，`web-research-router` 可以把当前/指定版本开发文档问题交给 Context7。

这样避免“Router 不触发 → Context7 永远不触发”的 bootstrap 问题。

## 6. Context7 风险触发策略

本项目不照搬官方 Skill 的“涉及库就查”策略，而采用：**有真实知识缺口再查。**

主动查询的典型场景：

- 用户明确指定版本；
- 大版本迁移、新旧 API 差异；
- deprecated / replaced API；
- Agent 即将根据记忆写第三方 API、配置项或 CLI 参数，但当前版本正确性不确定；
- Authentication、Security、ORM 高级配置、云 SDK、构建/部署等明显依赖当前框架行为的非平凡功能。

通常不主动查：

- 普通 Java/JavaScript/Python 基础代码；
- 纯业务逻辑；
- 简单重构/重命名；
- 项目内已有明确同版本实现；
- 当前上下文已经有可靠同版本资料。

同一任务内已确认的 `Library ID + Version + Topic` 应复用。单个问题原则上不超过 3 次 Context7 查询循环；仍不足则停止重复尝试并 fallback。

## 7. Web Research 两层 Router

### 第一层：Execution Router —— 谁来搜？

**主代理**：单点事实、少量文档/issue/release、低噪音、少量查询与来源即可确认。

**`web-searcher`**：多轮、多角度、多源核验、较多网页、社群/benchmark/竞品调查、或原始结果会明显污染主上下文。

关键规则：**不要仅因为主代理缺少 Native Search 就派子代理。先按工作量与噪音决定执行者。**

### 第二层：Retrieval Router —— 主代理用哪个后端？

**Native Web Search**：可用时，一般 Web、最新事实、浏览/导航、宿主原生页面交互默认优先。

**Exa Retrieval**：Native 不可用；语义/概念发现；长尾技术资料；GitHub/论文/开发者资料 discovery；严格 domain/date/category 过滤；或 Native 合理尝试后结果明显不足。

**Fallback**：只有首选结果明显不足才切另一后端；不要无目的双搜。

## 8. Router 为什么做成独立 Skill

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
- 能与 `exa-retrieval`、`context7-tech-docs` 一起通过 Plugin 分发；
- Router 与具体事实源 Skill 职责分离；
- 核心语义不绑定 Codex，迁移其它 Agent 宿主时只需调整宿主适配层。

AGENTS 仍保留极薄 bootstrap，以避免“为了知道是否该加载 Router Skill，先得加载 Router Skill”的循环依赖，同时提醒编码 Agent 遇到版本敏感第三方 API 时可直接使用 Context7。

## 9. 三种运行时接入

### 默认：Skill Router

```text
AGENTS thin bootstrap
      ↓ ambiguity / fallback / scope growth
web-research-router Skill
      ↓
executor + backend / fact-source choice
```

不创建规则目录。

### Inline

完整路由直接放 AGENTS；固定上下文略高，但最自足。

### File（兼容/偏好）

AGENTS 薄引用 + `web-research-router.md`。只有已有规则目录文化的团队才推荐使用，路径由 `--rules-dir` 指定。

## 10. Context7 CLI 与 Node 隔离

项目只依赖官方 CLI contract：

```bash
ctx7 library <library> "<query>"
ctx7 docs <library-id> "<query>"
```

不为 Context7 新增自有 API 客户端，也不注册 Context7 MCP。

### 10.1 Node 基线

Context7 顶层文档仍可能标注 CLI 需要 Node `>=18`，但当前依赖生态已经明显转向 Node 20+，Context7 MCP package 当前也要求 Node `>=20.18.1`。为了稳定给 Agent 使用，本项目建议：

```text
最低推荐：Node >=20.18.1
优先：Node 22 LTS（独立 Agent 工具环境）
```

不要为了 Context7 修改业务项目 Node 版本。

### 10.2 fnm 与同名 wrapper

如果系统已有可工作的官方 `ctx7`，直接复用。

只有 Node 版本冲突、PATH 不稳定或希望跨项目获得稳定工具入口时，才建议用 fnm 建立隔离环境。隔离环境可以提供同名 `ctx7` 透明 wrapper；它仍调用官方 CLI，只负责：

- 固定 Node 环境；
- 参数边界透传；
- stdout/stderr 透传；
- exit code 透传。

不负责 query rewrite、Library ID 选择、fallback、缓存、认证或路由。

因为 wrapper 自己也叫 `ctx7`，实现时必须避免再次依赖当前 PATH 解析裸 `ctx7` 而递归命中自身。

### 10.3 文档分层

- `skills/context7-tech-docs/references/node-isolation.md`：Direct/Plugin 安装后仍可按需读取的精简运行说明；
- `docs/CONTEXT7-NODE-ISOLATION.md`：仓库维护者与人工安装使用的完整说明。

## 11. 当前 Codex 集成示例

当前常见状态：主代理 custom GPT-5.6 无 Native，而 `web-searcher` GPT-5.4 有 Native：

```text
版本敏感第三方 API -> Context7
简单/低噪音 Web -> Main -> Exa
复杂/高噪音 Web -> web-searcher -> Native
```

未来主代理 Native 恢复：

```text
版本敏感第三方 API -> Context7
简单一般 Web -> Main -> Native
简单语义/长尾/精确过滤 -> Main -> Exa
复杂调研 -> web-searcher -> 其可用后端
```

第一层 Execution Router 不需要变化。

## 12. Exa 能力分层

Exa 当前核心能力映射为：

| 层级 | CLI | 默认披露 | 目的 |
|---|---|---:|---|
| 常用 | `find` | 是 | Search + highlights |
| 常用 | `read` | 是 | 读取已知 URL |
| 高级 | `advanced` | 否 | 日期/域名/category/搜索模式等 |
| 研究 | `research` | 否 | Exa Agent，多步研究 |

Deprecated MCP tools 不进入新 contract。

## 13. 双 Transport：REST 主路径 + Hosted MCP 匿名 fallback

运行时不是把 Exa MCP 注册给宿主，而是：

```text
Agent shell -> Python CLI -> Transport Router
                         -> REST API（有 EXA_API_KEY，优先）
                         -> Hosted MCP（无 Key，或 REST 配额临时耗尽）
```

这样保留两个目标：

1. 模型上下文只需要学习少量 CLI contract，不长期携带 MCP tool schema；
2. 用户没有 Exa Key 时仍可立即使用基础检索。

### 13.1 REST / quota fallback

`EXA_TRANSPORT=auto` 检测到 `EXA_API_KEY` 时优先 REST。

如果 REST 返回 Exa 官方定义的 402 配额/预算 tag（`NO_MORE_CREDITS`、`API_KEY_BUDGET_EXCEEDED`、`TEAM_BUDGET_EXCEEDED`），且该操作存在等价 Hosted MCP 能力，则临时切到**匿名 MCP**。429/401/403/5xx 不触发这一降级。降级状态默认保留 1 小时，到期自动 probe REST；probe 成功后清除状态并恢复 Key。显式 `EXA_TRANSPORT=api` 不做 fallback。

### 13.2 MCP session

Exa Hosted MCP 当前实际协商 MCP `2025-11-25`，仍是 session-based Streamable HTTP。CLI 缓存 `Mcp-Session-Id` 跨进程复用，不调用 `tools/list`；只有首次、缓存超过 20 小时或 session 失效时才重新 initialize。匿名与认证 session 分开缓存；402 fallback 强制匿名。

不引入 daemon：为节省一次握手而增加后台进程生命周期、端口、崩溃恢复和多项目并发复杂度，不符合本包轻量目标。

### 13.3 能力边界

- `find` / `read`：REST 或匿名 Hosted MCP。
- `advanced`：`auto/fast/instant` + 过滤可 MCP；deep 系列仅 REST + Key。
- `research`：Exa Agent REST，仅 Key。

### 13.4 UTF-8 I/O 契约

字符编码由 Exa CLI 自己负责，而不是交给宿主 shell 配置。REST/MCP 响应显式 UTF-8 解码，缓存文件显式 UTF-8，CLI 入口统一将 `stdout/stderr` 重配为 UTF-8。

Context7 使用官方 `ctx7` CLI；隔离/wrapper 场景把中文 query、中英混合、空格/引号参数、JSON、stdout/stderr 和 exit code 作为正式验收项，而不是把乱码 workaround 写进 Skill。

## 14. Progressive disclosure

- `exa-retrieval` 主 Skill 只教基础 `find/read` 与何时读取 advanced/research reference；
- `context7-tech-docs` 主 Skill 只教风险触发、`library -> docs` 流程、复用与 fallback；Node 隔离只在需要时读取 reference；
- `web-research-router` 只在路由不清、需要 fallback、或任务范围明显扩大时加载。

因此运行时上下文由任务需求决定，而不是把完整工具和规则长期注入。

## 15. Plugin / Direct

### Plugin

Codex Plugin 提供：

```text
skills/web-research-router
skills/exa-retrieval
skills/context7-tech-docs
```

### Direct

项目直接安装：

```text
.agents/skills/web-research-router
.agents/skills/exa-retrieval
.agents/skills/context7-tech-docs
.codex/agents/web-searcher.toml
```

File routing 风格时才额外创建：

```text
<rules-dir>/web-research-router.md
```

安装器只探测 `ctx7 --version`，不自动安装 Node/fnm/Context7，也不修改业务项目 Node 环境。Context7 CLI 未就绪只提示，不阻塞插件安装。

## 16. 安全与迁移

- `EXA_API_KEY` 缺失：基础能力自动使用 Hosted MCP；只有 API-only 能力明确报需要 Key。
- Context7 CLI 缺失：Skill 仍可安装；使用 Context7 前按官方 CLI/隔离说明准备 `ctx7`。
- Context7 Key 可选：基础查询可无认证，更高额度用 `ctx7 login` 或 `CONTEXT7_API_KEY`。
- 429/5xx：有限重试，不无限循环。
- deep：显式 `--allow-deep`。
- Exa Agent 新 run：显式 `--confirm-cost`。
- 已有 Skill/rule：不静默覆盖，内容不同生成 candidate。
- 已有 `web-searcher.toml`：始终保留原文件并生成候选版本供合并。
- AGENTS patch 使用 `web-research-router` marker，同时识别旧版 marker 并原位迁移。

## 17. 上游依据

核实日期：2026-08-25。

- Context7: https://github.com/upstash/context7
- Context7 CLI: https://github.com/upstash/context7/tree/master/packages/cli
- Context7 MCP package Node engine: https://github.com/upstash/context7/blob/master/packages/mcp/package.json
- Exa Search API: https://exa.ai/docs/reference/search
- Exa Contents API: https://exa.ai/docs/reference/get-contents
- Exa Agent: https://exa.ai/docs/reference/agent-api/create-a-run
- Exa MCP: https://github.com/exa-labs/exa-mcp-server
- OpenAI Codex Plugins: https://github.com/openai/plugins
- CodeAlive-AI/exa-skills: https://github.com/CodeAlive-AI/exa-skills
- HKUDS/CLI-Anything: https://github.com/HKUDS/CLI-Anything
