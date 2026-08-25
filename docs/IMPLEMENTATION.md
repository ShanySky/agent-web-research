# 落地方案

## 1. 推荐实施顺序

### A. 先验证 Exa CLI

基础检索可在不设置 `EXA_API_KEY` 时直接走 Hosted MCP；建议先分别测试匿名 MCP 与（若已有 Key）REST：

```bash
python skills/exa-retrieval/scripts/exa.py find "Codex latest release" -n 5
```

再测试 `read` 和一次 `advanced --include-domain github.com`。

### B. Direct dry-run

```bash
python scripts/install.py --project-root <PROJECT> --mode direct --dry-run
```

默认 routing style 是 `skill`，不会创建任何规则目录。

重点检查：

- 是否已有 `web-searcher.toml`；
- 是否已有 `web-research-router` / `exa-retrieval` Skill；
- `AGENTS.md` 是否已经有同义 Web Research 路由规则。

### C. 安装资产，不改 AGENTS

```bash
python scripts/install.py --project-root <PROJECT> --mode direct
```

默认安装两个 Skill 和候选/现有 `web-searcher`，但不修改 AGENTS。

### D. 加入最小 AGENTS bootstrap

推荐：

```bash
python scripts/install.py --project-root <PROJECT> --mode direct --patch-agents
```

等价于：

```bash
--routing-style skill
```

AGENTS 只保留最小路由提示；遇到歧义再加载 `web-research-router` Skill。

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

## 3. 从现有 AGENTS 规则迁移

旧规则如果是：

> 主代理没有网页检索工具时优先派 `web-searcher`。

新增 Exa 后应改成：

1. 先按任务规模和噪音判断 Main vs `web-searcher`；
2. Main 决定自己搜后，再判断 Native vs Exa；
3. Main 缺 Native 只意味着后端可能切到 Exa，不再自动等价于必须派子代理。

安装器 patch 会识别旧版 routing marker 并更新为新 `web-research-router` marker，避免留下两份规则。

## 4. `web-searcher` 合并重点

候选 agent 的定位：

- 从“Native 缺失兜底”改为“复杂研究/噪音隔离”；
- 使用它实际可用的网页检索能力；
- 返回实际检索后端；
- 不 dump 大量原始搜索结果；
- 保留 GPT-5.4、medium、read-only、官方/一手来源优先、日期意识、交叉核验和未知项明确等既有优点。

已有同名 agent 时绝不静默覆盖。

## 5. Plugin 模式

若当前 Codex 支持 Plugin CLI：

```bash
codex plugin marketplace add <KIT_ROOT>
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
```

项目级 `web-searcher.toml` 和 AGENTS bootstrap 仍由安装器处理。

若 Plugin 命令不可用、local marketplace 不稳定或 Skill 不可见，切回 Direct。安装/升级 Plugin 后建议新开会话验证 Skill discovery。

## 6. Exa CLI contract

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

## 6.1 Windows 字符编码

Exa CLI 内部固定 UTF-8 输出契约；项目不需要额外配置 shell 编码。维护脚本时必须保留：网络 UTF-8 解码、缓存 UTF-8 文件读写、CLI 入口 `stdout/stderr` UTF-8 重配，以及包含中文/特殊符号/emoji 的 GBK 外部环境回归测试。Python 源码中的注释与 docstring 继续保持英文。

## 7. 验证矩阵

| 场景 | 预期 |
|---|---|
| Main 无 Native，查一个 issue | Main -> Exa |
| Main 无 Native，调查多个社区反馈 | web-searcher -> 它可用的 Native/其它后端 |
| Main 有 Native，查今天发布信息 | Main -> Native |
| Main 有 Native，找语义相近/长尾资料 | Main -> Exa |
| 路由不明确或范围扩大 | 加载 `web-research-router` |
| Native 结果明显差 | Exa 补查 |
| Exa 精确过滤 | advanced；按需读 reference |
| 多步 Exa 研究 | research；显式成本确认 |

## 8. 回滚

Direct：

- 删除本包安装的 `.agents/skills/web-research-router`；
- 删除本包安装的 `.agents/skills/exa-retrieval`；
- 若使用 `file` 风格，删除对应 `web-research-router.md`；
- 删除/还原 AGENTS marker 区块；
- 对 `web-searcher.toml` 使用安装前版本，不要把 candidate 当备份源。

Plugin：

```bash
codex plugin remove agent-web-research@agent-web-research
```

然后回滚项目级 agent/AGENTS 资产。

## 9. 项目 AI 可调整项

允许按项目调整：

- Skill 安装目录；
- 若使用 file 风格，规则目录；
- `web-searcher` 模型和 reasoning effort；
- “复杂研究”的阈值；
- 是否保留 Exa `research`；
- 输出长度默认值。

不建议随意改变：

- “先执行者、后后端”的两层顺序；
- Native / Exa / `web-searcher` / Router Skill 的职责隔离；
- “结果不足才 fallback”；
- cost gate；
- 不静默覆盖项目资产。


## Transport 运维

- 默认 `EXA_TRANSPORT=auto`。
- `auto`：有 Key → REST；无 Key → Hosted MCP。
- 有 Key 时若 REST 返回三类官方 402 quota/budget tag，`find/read/常规 advanced` 临时降级到匿名 Hosted MCP；默认 3600 秒后自动 probe REST，成功即恢复。
- 429/401/403/5xx 不触发 quota fallback；显式 `EXA_TRANSPORT=api` 不 fallback。
- 可用 `EXA_API_QUOTA_PROBE_SECONDS` 调整恢复探测间隔；`0` 表示每次都重新 probe。
- 排障可临时设 `EXA_TRANSPORT=mcp` 或 `api`。
- MCP session 与 quota-state cache 默认位于用户 cache 目录，不写入项目，不应提交 Git；匿名/认证 MCP session 分离。
- session 失效会自动重建一次；不需要手工启动/停止 daemon。
- deep advanced / research 仍需 `EXA_API_KEY`。
