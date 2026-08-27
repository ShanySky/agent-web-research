# 落地方案

## 1. 推荐实施顺序

### A. 先验证 Exa CLI

基础检索可在不设置 `EXA_API_KEY` 时直接走 Hosted MCP；建议先分别测试匿名 MCP 与（若已有 Key）REST：

```bash
python skills/exa-retrieval/scripts/exa.py find "Codex latest release" -n 5
```

再测试 `read` 和一次 `advanced --include-domain github.com`。

### B. 检查 Context7 CLI

Context7 使用官方 `ctx7` CLI，不新增 Context7 MCP。

```bash
ctx7 --version
ctx7 library react "useEffect cleanup"
```

如果 `ctx7` 已经可用，直接复用。若不可用，不要为了 Context7 修改业务项目 Node 版本。

本项目推荐：

```text
最低推荐 Node：20.18.1+
优先隔离环境：Node 22 LTS
```

需要 Node 隔离时参见：

```text
docs/CONTEXT7-NODE-ISOLATION.md
```

fnm 是推荐方案，不是强制依赖。

### C. Direct dry-run

```bash
python scripts/install.py --project-root <PROJECT> --mode direct --dry-run
```

默认 routing style 是 `skill`，不会创建任何规则目录。

重点检查：

- 是否已有 `web-searcher.toml`；
- 是否已有 `web-research-router` / `exa-retrieval` / `context7-tech-docs` Skill；
- `AGENTS.md` 是否已经有同义 Web Research / 技术文档校准规则；
- PATH 中是否已有可工作的官方 `ctx7`。

`ctx7` 不存在不会让安装失败，只表示 Context7 Skill 暂时不可执行。

### D. 安装资产，不改 AGENTS

```bash
python scripts/install.py --project-root <PROJECT> --mode direct
```

默认安装三个 Skill 和候选/现有 `web-searcher`，但不修改 AGENTS。

### E. 加入最小 AGENTS bootstrap

推荐：

```bash
python scripts/install.py --project-root <PROJECT> --mode direct --patch-agents
```

等价于：

```bash
--routing-style skill
```

AGENTS 只保留最小路由提示；遇到 Web Research 歧义再加载 `web-research-router` Skill。版本敏感或不确定的第三方 API/配置可直接触发 `context7-tech-docs`，不要求先经过 Router。

## 2. 可选接入风格

### Inline

```bash
python scripts/install.py --project-root <PROJECT> --patch-agents --routing-style inline
```

不依赖 Router Skill 的正文也能理解完整路由，但固定提示更长。

### File

如果团队已有规则目录：

```bash
python scripts/install.py \
  --project-root <PROJECT> \
  --patch-agents \
  --routing-style file \
  --rules-dir .agents/custom-rules
```

生成：

```text
.agents/custom-rules/web-research-router.md
```

也可以指定任意目录；`thin` 保留为 `file` 的旧别名。

## 3. 信息路由基线

先区分：

```text
当前/指定版本技术事实
→ Context7

开放互联网动态/讨论/发现
→ Web Research Router
```

### Context7

适合：

- Library / Framework / SDK / API / CLI；
- 指定版本文档；
- Configuration；
- Migration；
- deprecated / replaced API；
- Agent 准备根据记忆编写第三方 API/配置，但当前版本正确性不确定。

不采用“逢库必查”。普通语言基础、纯业务逻辑、简单重构、项目内已有可靠同版本实现时无需主动查询。

### Web Research

1. 先按任务规模和噪音判断 Main vs `web-searcher`；
2. Main 决定自己搜后，再判断 Native vs Exa；
3. Main 缺 Native 只意味着后端可能切到 Exa，不再自动等价于必须派子代理。

## 4. Context7 Skill 使用原则

标准流程：

```bash
ctx7 library <library> "<query>"
ctx7 docs <library-id> "<query>"
```

需要机器可读结果时使用 `--json`。

规则：

- 除非已经有可靠 Library ID，否则先 `library` 再 `docs`；
- Query 一次聚焦一个主题；
- 当前任务内复用已确认的 `Library ID + Version + Topic`；
- 版本、主题、资料充分性或实际行为发生变化时再查；
- 单个问题原则上不超过 3 次 Context7 查询循环；
- 不把 API Key、密码、个人数据或专有代码放进 query；
- Context7 结果不足或服务失败时，不阻塞任务，回退官方文档 / GitHub / Native / Exa。

## 5. Context7 Node / fnm / wrapper

优先级：

1. 系统已有可工作的官方 `ctx7` → 直接使用；
2. Node 版本冲突或 PATH 不稳定 → 使用 fnm 建独立 Agent 工具环境；
3. 只有需要让 Agent 在不同项目中始终执行同一个 `ctx7` 时，才创建同名透明 wrapper。

推荐：

```bash
fnm install 22
fnm exec --using=22 npm install -g ctx7@latest
fnm exec --using=22 ctx7 --version
```

wrapper 只负责固定 Node 环境与完整参数/stdout/stderr/exit code 透传。它不负责 query rewrite、Library ID 选择、fallback、缓存、认证或路由。

因为 wrapper 本身也叫 `ctx7`，不要在内部再次依赖当前 PATH 执行裸 `ctx7`，避免递归命中自身；必须确认调用的是隔离环境中的官方 CLI 确定入口。

Windows 验收至少覆盖：中文 query、英文 query、中英混合、带空格/引号参数、JSON、stdout/stderr、非 0 exit code。

## 6. 从现有 AGENTS 规则迁移

旧规则如果是：

> 主代理没有网页检索工具时优先派 `web-searcher`。

新增 Exa / Context7 后应改成：

1. 版本敏感第三方技术事实 → `context7-tech-docs`；
2. 其它 Web Research 先按任务规模和噪音判断 Main vs `web-searcher`；
3. Main 决定自己搜后，再判断 Native vs Exa；
4. Main 缺 Native 不再自动等价于必须派子代理。

安装器 patch 会识别旧版 routing marker 并更新为新 `web-research-router` marker，避免留下两份规则。

## 7. `web-searcher` 合并重点

候选 agent 的定位：

- 从“Native 缺失兜底”改为“复杂研究/噪音隔离”；
- 使用它实际可用的网页检索能力；
- 返回实际检索后端；
- 不 dump 大量原始搜索结果；
- 保留 GPT-5.4、medium、read-only、官方/一手来源优先、日期意识、交叉核验和未知项明确等既有优点。

已有同名 agent 时绝不静默覆盖。

## 8. Plugin 模式

若当前 Codex 支持 Plugin CLI：

```bash
codex plugin marketplace add <REPO_ROOT>
codex plugin add agent-web-research@agent-web-research
```

或：

```bash
python scripts/install.py --project-root <PROJECT> --mode plugin --patch-agents
```

Plugin 提供：

```text
web-research-router
exa-retrieval
context7-tech-docs
```

项目级 `web-searcher.toml` 和 AGENTS bootstrap 仍由安装器处理。

若 Plugin 命令不可用、local marketplace 不稳定或 Skill 不可见，切回 Direct。安装/升级 Plugin 后建议新开会话验证 Skill discovery。

## 9. Exa CLI contract

### 基础：find

```bash
python <skill-dir>/scripts/exa.py find QUERY [-n N] [--category CATEGORY] [--json]
```

### 基础：read

```bash
python <skill-dir>/scripts/exa.py read URL [URL ...] [--max-chars N] [--json]
```

### 高级：advanced

```bash
python <skill-dir>/scripts/exa.py advanced QUERY [filters...]
```

支持搜索类型、include/exclude domain、发布日期、category、location、additional query、content mode、freshness 等。Deep 模式必须 `--allow-deep`。

### 研究：research

```bash
python <skill-dir>/scripts/exa.py research QUERY --confirm-cost
```

新 Exa Agent run 必须显式成本确认；已有 `run-id` 可只查询状态。

### Windows 字符编码

Exa CLI 内部固定 UTF-8 输出契约；项目不需要额外配置 shell 编码。维护脚本时必须保留：网络 UTF-8 解码、缓存 UTF-8 文件读写、CLI 入口 `stdout/stderr` UTF-8 重配，以及包含中文/特殊符号/emoji 的 GBK 外部环境回归测试。Python 源码中的注释与 docstring 继续保持英文。

## 10. 验证矩阵

| 场景 | 预期 |
|---|---|
| 指定 Spring Boot 版本配置 | `context7-tech-docs` -> ctx7 |
| Agent 对第三方 API 当前用法不确定 | 编码前主动 Context7 校准 |
| Context7 已有同版本同主题资料 | 复用，不重复查 |
| Context7 找不到/结果不足 | fallback 官方文档 / GitHub / Native / Exa |
| Main 无 Native，查一个 issue | Main -> Exa |
| Main 无 Native，调查多个社区反馈 | web-searcher -> 它可用的 Native/其它后端 |
| Main 有 Native，查今天发布信息 | Main -> Native |
| Main 有 Native，找语义相近/长尾资料 | Main -> Exa |
| 路由不明确或范围扩大 | 加载 `web-research-router` |
| Native 结果明显差 | Exa 补查 |
| Exa 精确过滤 | advanced；按需读 reference |
| 多步 Exa 研究 | research；显式成本确认 |

## 11. 回滚

Direct：

- 删除本包安装的 `.agents/skills/web-research-router`；
- 删除本包安装的 `.agents/skills/exa-retrieval`；
- 删除本包安装的 `.agents/skills/context7-tech-docs`；
- 若使用 `file` 风格，删除对应 `web-research-router.md`；
- 删除/还原 AGENTS marker 区块；
- 对 `web-searcher.toml` 使用安装前版本，不要把 candidate 当备份源。

Context7 CLI 本身由用户环境管理；如果是全局 npm 安装，可按 Context7 官方方式卸载。不要让本插件安装器自动删除用户已有 `ctx7`。

Plugin：

```bash
codex plugin remove agent-web-research@agent-web-research
```

然后回滚项目级 agent/AGENTS 资产。

## 12. 项目 AI 可调整项

允许按项目调整：

- Skill 安装目录；
- 若使用 file 风格，规则目录；
- `web-searcher` 模型和 reasoning effort；
- “复杂研究”的阈值；
- Context7 主动查询阈值；
- 是否保留 Exa `research`；
- 输出长度默认值；
- Context7 隔离 Node 版本，只要不低于推荐基线且已验证稳定。

不建议随意改变：

- “版本敏感技术事实 → Context7；开放互联网动态 → Web Research”的职责边界；
- “先执行者、后后端”的 Web Research 两层顺序；
- Native / Exa / `web-searcher` / Router Skill 的职责隔离；
- “结果不足才 fallback”；
- cost gate；
- 不静默覆盖项目资产；
- 不为了 Context7 改业务项目 Node 环境。

## 13. Transport 运维

- 默认 `EXA_TRANSPORT=auto`。
- `auto`：有 Key → REST；无 Key → Hosted MCP。
- 有 Key 时若 REST 返回三类官方 402 quota/budget tag，`find/read/常规 advanced` 临时降级到匿名 Hosted MCP；默认 3600 秒后自动 probe REST，成功即恢复。
- 429/401/403/5xx 不触发 quota fallback；显式 `EXA_TRANSPORT=api` 不 fallback。
- 可用 `EXA_API_QUOTA_PROBE_SECONDS` 调整恢复探测间隔；`0` 表示每次都重新 probe。
- 排障可临时设 `EXA_TRANSPORT=mcp` 或 `api`。
- MCP session 与 quota-state cache 默认位于用户 cache 目录，不写入项目，不应提交 Git；匿名/认证 MCP session 分离。
- session 失效会自动重建一次；不需要手工启动/停止 daemon。
- deep advanced / research 仍需 `EXA_API_KEY`。

Context7 不走上述 Exa transport。它由官方 `ctx7` CLI 自行处理服务访问；更高额度可使用 `ctx7 login` 或 `CONTEXT7_API_KEY`。
