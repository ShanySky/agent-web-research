# Changelog

本项目遵循语义化版本思路维护版本记录。

## [0.7.0] - 2026-08-25

### Added
- `context7-tech-docs` Skill：用于 Library / Framework / SDK / API / CLI 的版本敏感技术文档校准。
- Context7 风险触发策略：版本敏感、迁移、deprecated API、复杂第三方框架功能或当前 API 行为不确定时主动查询；不采用“逢库必查”。
- Context7 官方 `ctx7` CLI 集成：`ctx7 library` → `ctx7 docs`，不新增 Context7 MCP。
- Context7 Node 隔离说明：推荐 Node `>=20.18.1`，优先 Node 22 LTS；支持 fnm 隔离与同名 `ctx7` 透明 wrapper。
- Skill 内置 `references/node-isolation.md`，Direct 安装后仍可按需读取隔离说明。
- 安装器/验证器增加 `ctx7` 可用性探测；Context7 CLI 未就绪时只提示，不阻塞整个插件安装。

### Changed
- `web-research-router` 增加 Context7 边界：当前/指定版本的 API、配置、CLI、迁移与开发文档优先 Context7；Release、Issue、社区反馈、博客、新闻、项目发现继续走 Web/GitHub/Exa。
- AGENTS 三种接入模板同步加入极薄的 Context7 技术校准提示。
- `agent-web-research` 插件元数据升级到 `0.7.0`，定位从“Web + Exa”扩展为“Web Research + Exa + 版本敏感开发文档”。
- Context7 作为独立 Skill 可在编码过程中主动触发，不要求先经过 `web-research-router`。

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
