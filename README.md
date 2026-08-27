# Agent Web Research

面向 AI Agent 的轻量 Web Research 插件与检索工具集。

它把几类能力分开处理：

- `web-research-router`：判断**谁来搜**，以及主代理自行检索时**用哪个后端**；
- `exa-retrieval`：提供 Exa 语义检索、网页读取、高级过滤与研究能力；
- `context7-tech-docs`：使用官方 `ctx7` CLI 做版本敏感的第三方技术文档校准；
- `web-searcher`：用于多轮、多源、高噪音 Web Research，把原始搜索上下文隔离在子代理中。

当前插件版本：**0.7.0**。

## 为什么做这个项目

一些 Agent 宿主在使用自定义模型时，原生 Web Search 可能不可用；另一方面，把完整 Exa / Context7 MCP 长期挂到所有 Agent 上又会增加工具上下文和维护负担。

本项目采用 CLI + Skill 的方式，把不同类型的信息需求拆开：

```text
Agent / Coding Agent
    │
    ├─ 当前/指定版本第三方技术文档
    │      └─ context7-tech-docs
    │             └─ 官方 ctx7 CLI
    │
    ├─ Web Research 路由
    │      └─ web-research-router
    │             ├─ Main Agent
    │             └─ web-searcher
    │
    ├─ Native Web Search（宿主可用时）
    │
    └─ exa-retrieval
           └─ Python CLI
                ├─ REST API（有 EXA_API_KEY 时优先）
                └─ Hosted MCP（无 Key 或配额耗尽时匿名 fallback）
```

核心目标是：**降低固定上下文负担、保持路由可预测，让开放互联网检索与版本敏感开发文档各司其职。**

## 仓库结构

```text
agent-web-research/
├─ .codex-plugin/
│  └─ plugin.json
├─ .agents/plugins/
│  └─ marketplace.json
├─ skills/
│  ├─ web-research-router/
│  ├─ exa-retrieval/
│  └─ context7-tech-docs/
├─ templates/
│  ├─ agents/web-searcher.toml
│  ├─ rules/web-research-router.md
│  └─ snippets/
├─ scripts/
│  ├─ install.py
│  ├─ verify.py
│  └─ build_release.py
├─ tests/
├─ docs/
│  └─ CONTEXT7-NODE-ISOLATION.md
├─ CHANGELOG.md
├─ LICENSE
└─ README.md
```

仓库根目录就是插件根目录，适合单插件仓库长期维护。

## 快速开始

### 1. Clone

```bash
git clone https://github.com/ShanySky/agent-web-research.git
cd agent-web-research
```

### 2. 先做 dry-run

```bash
python scripts/install.py --project-root <PROJECT_ROOT> --dry-run
```

### 3. 推荐：Direct 安装

```bash
python scripts/install.py \
  --project-root <PROJECT_ROOT> \
  --mode direct \
  --patch-agents
```

默认会：

- 安装 `web-research-router`、`exa-retrieval`、`context7-tech-docs` 三个 Skill；
- 安装或生成候选版 `web-searcher.toml`；
- 仅在显式 `--patch-agents` 时修改 `AGENTS.md`；
- 默认不创建独立规则目录；
- 检查 PATH 中是否已有可工作的官方 `ctx7`，但**不会自动安装 Node、fnm 或 Context7，也不会修改业务项目 Node 环境**。

Windows PowerShell 示例：

```powershell
python .\scripts\install.py --project-root C:\path\to\project --mode direct --patch-agents
```

如果暂时不准备启用 Context7，可跳过运行时检查：

```bash
python scripts/install.py --project-root <PROJECT_ROOT> --skip-context7-check
```

Skill 仍会安装，之后准备好 `ctx7` 即可使用。

### 4. Codex Plugin 安装

如果当前 Codex 已支持 Plugin CLI，可以把本仓库作为本地 marketplace：

```bash
codex plugin marketplace add <REPO_ROOT>
codex plugin add agent-web-research@agent-web-research
```

也可以让安装器执行：

```bash
python scripts/install.py \
  --project-root <PROJECT_ROOT> \
  --mode plugin \
  --patch-agents
```

插件模式负责三个 Skill；项目级 `web-searcher.toml` 与 `AGENTS.md` bootstrap 仍由安装器安全落地。

> Codex Plugin / Marketplace 机制仍在演进。若当前 Codex 构建的 Plugin 发现行为异常，可使用 Direct 模式；两种模式使用同一套 Skill 源码。

## Context7：版本敏感技术文档

Context7 不替代 Exa 或一般 Web Search。它主要处理：

- Library / Framework / SDK / API / CLI；
- 指定版本文档；
- API 与配置用法；
- deprecated / replaced API；
- 版本迁移；
- 编码前对第三方框架当前行为做技术事实校准。

简单原则：

```text
“这个技术在当前/指定版本应该怎么正确使用？” → Context7
“外界最近关于这个技术发生了什么？”             → Web / GitHub / Exa
```

例如：

```text
Spring Boot 3.x 某配置怎么写        → Context7
某 API 在当前版本是否 deprecated    → Context7
Next.js 某版本 middleware 怎么使用  → Context7

Spring Boot 最近发布了什么版本      → Web / Release
某版本最近有什么严重 Bug            → GitHub Issue / Web
社区对某版本评价如何                 → Exa / Web
```

本项目采用**风险触发**，不是“逢库必查”：版本敏感、迁移、复杂第三方框架功能，或 Agent 对当前 API/配置存在真实不确定时主动查询；普通语言基础、纯业务逻辑、简单重构、项目内已有可靠同版本实现时无需查询。

### Context7 CLI

直接使用官方 CLI：

```bash
ctx7 library <library> "<query>"
ctx7 docs <library-id> "<query>"
```

机器可读结果可使用 `--json`。

安装官方 CLI：

```bash
npm install -g ctx7@latest
```

Context7 顶层文档仍可能写 Node 18+，但当前依赖生态已经明显向 Node 20+ 演进。为了稳定给 Agent 使用，本项目建议：

- **最低推荐 Node 20.18.1+**；
- 新建独立 Agent 工具环境时优先 **Node 22 LTS**；
- 不要为了 Context7 修改业务项目自己的 Node 版本。

如果项目 Node 较旧或希望获得稳定的跨项目 `ctx7` 命令，可使用 fnm 建立隔离工具环境。安装、维护与验收说明统一参见：[Context7 Node 隔离与 ctx7 稳定入口](docs/CONTEXT7-NODE-ISOLATION.md)。

隔离场景允许使用**同名 `ctx7` 透明 wrapper**；它仍调用官方 CLI，只负责固定 Node 环境、参数/stdout/stderr/exit code 透传，不承载路由、缓存、fallback 或查询逻辑。

### Context7 认证

基础文档查询可无认证使用。需要更高额度时可：

```bash
ctx7 login
```

或设置：

```text
CONTEXT7_API_KEY
```

凭证不要写入项目仓库、Skill 或 AGENTS.md。

## Exa Key：可选

基础 Exa 检索不要求必须配置 Key。

默认：

```text
EXA_TRANSPORT=auto
```

行为：

- 有 `EXA_API_KEY`：优先使用 Exa REST API；
- 没有 Key：使用 Exa Hosted MCP 匿名能力；
- REST 返回 Exa 明确的 402 配额/预算耗尽错误时，支持等价执行的操作会临时切到匿名 MCP；
- 降级状态到期后自动重新 probe REST，额度恢复后自动切回 Key；
- `deep-*` 与 `research` 等没有匿名等价能力的操作仍需要有效 Key。

Windows 永久设置用户级 Key：

```powershell
setx EXA_API_KEY "your-key"
```

重新打开终端/VS Code/Codex 后生效。

## 常用 Exa CLI

```bash
python skills/exa-retrieval/scripts/exa.py find "query" -n 5
python skills/exa-retrieval/scripts/exa.py read "https://example.com/page"
```

高级过滤：

```bash
python skills/exa-retrieval/scripts/exa.py advanced \
  "Codex custom provider web search" \
  --include-domain github.com \
  --after 2026-07-01 \
  -n 10
```

Exa Agent 研究需要显式成本确认：

```bash
python skills/exa-retrieval/scripts/exa.py research \
  "Compare recent web-search regressions" \
  --effort low \
  --confirm-cost
```

## 路由原则

### 1. 先看是否属于版本敏感开发文档

当前/指定版本的 Library、Framework、SDK、API、CLI、配置或迁移事实，优先使用 `context7-tech-docs`。

Release 动态、Bug/Issue、社区反馈、新闻、博客、项目发现等开放互联网问题继续进入 Web Research 路由。

### 2. Web Research 再决定谁来搜

- 简单、低噪音、少量来源：主代理；
- 多轮、多源、benchmark / 社群 / 竞品调查、预期大量网页内容：`web-searcher`。

### 3. 主代理自行 Web Research 时选择后端

- 一般 Web、最新事实、网页浏览：Native Web Search 可用时优先；
- Native 不可用，或语义/概念发现、长尾技术资料、GitHub/论文 discovery、严格过滤：Exa；
- 首选结果明显不足才 fallback，避免无目的双搜。

详细运行规则由 `web-research-router` Skill 按需加载；`context7-tech-docs` 也可以在编码过程中独立主动触发，不要求先经过 Router。

## 可选规则文件模式

默认推荐 Router Skill，不要求团队接受某个固定规则目录。

如果团队已经有自己的规则目录，可使用：

```bash
python scripts/install.py \
  --project-root <PROJECT_ROOT> \
  --routing-style file \
  --rules-dir docs/agent-rules \
  --patch-agents
```

规则文件固定命名为：

```text
web-research-router.md
```

## Windows UTF-8

Exa Python CLI 自己保证 UTF-8 I/O：REST/MCP 解码、`stdout/stderr`、JSON 和本地 cache 都显式使用 UTF-8。用户不需要为本插件额外修改 PowerShell/CMD code page。

Context7 使用官方 `ctx7` CLI；若采用 Node 隔离/wrapper，中文 query、中英混合、带空格参数、JSON、stdout/stderr 和 exit code 都属于正式验收项，不把乱码 workaround 写进 Skill。

## 验证

项目安装后：

```bash
python scripts/verify.py --project-root <PROJECT_ROOT>
```

运行全部离线测试：

```bash
python -m unittest discover -s tests -v
```

真实 Exa smoke test：

```bash
python tests/live_smoke.py --transport mcp
```

API 路径：

```bash
python tests/live_smoke.py --transport api
```

后者需要 `EXA_API_KEY`。

Context7 可直接验证：

```bash
ctx7 --version
ctx7 library react "useEffect cleanup"
```

## Release

Release 包不提交到 Git。使用：

```bash
python scripts/build_release.py
```

默认会先运行测试与基础校验，然后生成：

```text
dist/agent-web-research-v<version>.zip
```

仅打包、不运行测试：

```bash
python scripts/build_release.py --skip-tests
```

GitHub 发布建议：

```text
修改版本与 CHANGELOG
→ 运行测试
→ git tag vX.Y.Z
→ python scripts/build_release.py
→ 创建 GitHub Release
→ 上传 dist/*.zip
```

## 文档

- [设计方案](docs/DESIGN.md)
- [落地方案](docs/IMPLEMENTATION.md)
- [Context7 Node 隔离](docs/CONTEXT7-NODE-ISOLATION.md)
- [复用审计](docs/REUSE-AUDIT.md)
- [来源与兼容性依据](docs/SOURCES.md)
- [验证记录](docs/VALIDATION.md)
- [版本记录](CHANGELOG.md)

## License

MIT，见 [LICENSE](LICENSE)。
