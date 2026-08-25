# Changelog

本项目遵循语义化版本思路维护版本记录。

## [0.6.0] - 2026-08-25

### Added
- `web-research-router` Skill：两层 Web Research 路由。
- `exa-retrieval` Skill 与 Python CLI：`find`、`read`、`advanced`、`research`。
- Exa REST + Hosted MCP 双 transport。
- 无 Key 匿名 Hosted MCP fallback。
- REST 402 配额耗尽后的临时匿名 fallback 与自动 REST 恢复探测。
- MCP session 跨 CLI 进程缓存与失效自动重建。
- `web-searcher` 项目级子代理模板。
- Direct / Codex Plugin 双安装模式。
- Router Skill、inline、独立规则文件三种 AGENTS 接入方式。
- Windows UTF-8 CLI I/O 兼容与 GBK 外部环境回归测试。
- 安全安装策略：同名 Agent/Skill 冲突时保留现状并生成 candidate。

### Changed
- 两个 Skill 的说明内容改为中文优先，机器接口与代码标识保留英文。
- `web-research-router` 成为默认路由规则载体；独立规则目录降级为可选模式。
- 插件正式名称统一为 `agent-web-research`。

### Repository packaging
- 将原 `agent-web-research-kit` 交付包重构为单插件 GitHub 仓库结构。
- 插件根提升到仓库根目录。
- 设计/实施/验证资料移动到 `docs/`。
- 项目安装模板移动到 `templates/`。
- 安装/验证/Release 工具集中到 `scripts/`。
