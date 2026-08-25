# Agent Web Research

面向 AI Agent 的轻量 Web Research 插件与检索工具集。

它把三件事分开处理：

- `web-research-router`：判断**谁来搜**，以及主代理自行检索时**用哪个后端**；
- `exa-retrieval`：提供 Exa 语义检索、网页读取、高级过滤与研究能力；
- `web-searcher`：用于多轮、多源、高噪音 Web Research，把原始搜索上下文隔离在子代理中。

当前插件版本：**0.6.0**。

## 为什么做这个项目

一些 Agent 宿主在使用自定义模型时，原生 Web Search 可能不可用；另一方面，把完整 Exa MCP 长期挂到所有 Agent 上又会增加工具上下文和维护负担。

本项目采用：

```text
Agent / Codex
    │
    ├─ Native Web Search（可用时）
    │
    ├─ web-research-router
    │      ├─ Main Agent
    │      └─ web-searcher
    │
    └─ exa-retrieval
           └─ Python CLI
                ├─ REST API（有 EXA_API_KEY 时优先）
                └─ Hosted MCP（无 Key 或配额耗尽时匿名 fallback）
```

核心目标是：**降低固定上下文负担、保持路由可预测，并让 Exa 在没有 API Key 时也能先用起来。**

## 仓库结构

```text
agent-web-research/
├─ .codex-plugin/
│  └─ plugin.json
├─ .agents/plugins/
│  └─ marketplace.json
├─ skills/
│  ├─ web-research-router/
│  └─ exa-retrieval/
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
├─ CHANGELOG.md
├─ LICENSE
└─ README.md
```

仓库根目录就是插件根目录，不再额外套一层 `plugins/agent-web-research/`。这更适合单插件仓库长期维护。

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

- 安装 `web-research-router` 与 `exa-retrieval` 两个 Skill；
- 安装或生成候选版 `web-searcher.toml`；
- 仅在显式 `--patch-agents` 时修改 `AGENTS.md`；
- 默认不创建独立规则目录。

Windows PowerShell 示例：

```powershell
python .\scripts\install.py --project-root C:\path\to\project --mode direct --patch-agents
```

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

插件模式负责两个 Skill；项目级 `web-searcher.toml` 与 `AGENTS.md` bootstrap 仍由安装器安全落地。

> Codex Plugin / Marketplace 机制仍在演进。若当前 Codex 构建的 Plugin 发现行为异常，可使用 Direct 模式；两种模式使用同一套 Skill 源码。

## Exa Key：可选

基础检索不要求你必须配置 Key。

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

## 两层路由

第一层先决定**谁来搜**：

- 简单、低噪音、少量来源：主代理；
- 多轮、多源、benchmark / 社群 / 竞品调查、预期大量网页内容：`web-searcher`。

第二层仅在主代理自行检索时决定**用哪个后端**：

- 一般 Web、最新事实、网页浏览：Native Web Search 可用时优先；
- Native 不可用，或语义/概念发现、长尾技术资料、GitHub/论文 discovery、严格过滤：Exa；
- 首选结果明显不足才 fallback，避免无目的双搜。

详细运行规则由 `web-research-router` Skill 按需加载。

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

CLI 自己保证 UTF-8 I/O：REST/MCP 解码、`stdout/stderr`、JSON 和本地 cache 都显式使用 UTF-8。用户不需要为本插件额外修改 PowerShell/CMD code page。

Windows GBK 外部环境下的中文、特殊符号、日韩字符与 emoji 已纳入离线回归测试。

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
- [复用审计](docs/REUSE-AUDIT.md)
- [来源与兼容性依据](docs/SOURCES.md)
- [验证记录](docs/VALIDATION.md)
- [版本记录](CHANGELOG.md)

## License

MIT，见 [LICENSE](LICENSE)。
