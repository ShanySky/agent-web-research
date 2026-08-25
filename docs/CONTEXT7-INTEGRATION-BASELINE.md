# Context7 集成实施基线

本文记录 v0.7.0 Context7 集成的最小设计基线，避免后续维护时重新把边界做复杂。

## 已确定

- Context7 作为**版本敏感开发文档事实源**，不替代 Exa / Native Web Search。
- 使用官方 `ctx7` CLI + Skill，不新增 Context7 MCP。
- `context7-tech-docs` 可以在编码过程中独立主动触发，不要求先经过 `web-research-router`。
- 触发策略采用“有真实知识缺口再查”，不采用“逢库必查”。
- 当前/指定版本的 Library / Framework / SDK / API / CLI、配置、迁移、deprecated/replaced API → Context7。
- Release、Issue、社区评价、博客、新闻、项目发现 → 现有 Web Research 路径。
- 同一任务内复用已确认的 `Library ID + Version + Topic`，不做持久 Library ID cache。
- Context7 失败不能阻塞任务，可回退官方文档、GitHub、Native Web Search 或 Exa。
- 安装器只探测 `ctx7` 是否可用，不自动安装 Node、fnm、Context7，不修改业务项目 Node 环境。
- Context7 顶层文档仍可能标注 Node 18+；本项目为稳定性推荐 Node `>=20.18.1`，独立工具环境优先 Node 22 LTS。
- fnm 是推荐隔离方式，不是强制依赖。
- 确有隔离需求时可以提供同名 `ctx7` 透明 wrapper；wrapper 只负责固定 Node 环境和参数/stdout/stderr/exit code 透传。
- wrapper 不承担 query rewrite、Library ID 选择、fallback、缓存、认证或路由；实现时必须避免同名递归。

## 保持不变

- Web Research 仍先决定 Main vs `web-searcher`，再在 Main 内决定 Native vs Exa。
- Exa REST / Hosted MCP 双 transport、quota fallback、session cache 与 UTF-8 逻辑不因 Context7 改造而变化。
- 默认仍使用 Router Skill，不要求项目接受固定规则目录。
