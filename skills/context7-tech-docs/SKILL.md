---
name: context7-tech-docs
description: 使用 Context7 查询 Library、Framework、SDK、API、CLI 等当前或指定版本的技术文档。涉及版本敏感用法、迁移、deprecated API、配置项，或准备依据记忆编写但对第三方 API 当前行为不确定时使用；普通语言基础、纯业务逻辑、简单重构或已有可靠同版本资料时无需查询。
---

# Context7 技术文档校准

把 Context7 当作**版本敏感的开发文档事实源**，而不是通用 Web Search。目标是存在真实知识缺口时先校准技术事实，再继续编码；不要因为任务里出现第三方库名称就机械查询。

## 什么时候主动使用

- 用户明确指定 Library / Framework / SDK / API / CLI 的版本；
- 大版本迁移、新旧 API 差异、deprecated / replaced API；
- 准备根据记忆编写第三方 API、配置项、CLI 参数或框架特定代码，但不能确认当前版本仍然正确；
- Authentication、Security、ORM 高级配置、云 SDK、构建/部署等明显依赖当前框架行为的非平凡功能。

以下情况通常不需要主动查询：普通 Java/JavaScript/Python 基础代码、纯业务逻辑、简单重构/重命名、项目内已有明确同版本实现，或当前上下文已经有可靠的同版本资料。

## 标准流程

Agent 只依赖 PATH 中可工作的官方 `ctx7` 命令：

```bash
ctx7 library <library> "<query>"
ctx7 docs <library-id> "<query>"
```

需要机器可读结果时使用 `--json`。除非用户已经给出有效的 Context7 Library ID（`/org/project` 或版本化 ID），否则先执行 `library` 再执行 `docs`。

查询要具体、一次聚焦一个主题；不要把 API Key、密码、凭证、个人数据或专有代码放入查询。

## 版本与复用

如果 `library` 结果提供了与用户指定版本匹配的 Library ID，优先使用版本化 ID。当前任务内已确认的 `Library ID + Version + Topic` 应复用，不要每写一个类就重新查询。

只有版本、主题或资料充分性发生变化，出现新的 API 疑问，或实际运行结果与已有认知冲突时再查。单个问题原则上不超过 3 次 Context7 查询循环；仍不足时停止重复尝试并使用现有 Web/GitHub/官方资料补查。

## 与 Web Research 的边界

- 当前/指定版本的 API、配置、CLI、迁移与官方开发文档用法 → Context7。
- 最新 Release 动态、Bug/Issue、社区评价、博客、新闻、项目发现 → `web-research-router` 所管理的 Native Web Search / Exa / GitHub 等开放互联网路径。

Context7 结果不足或 CLI/服务失败时不要阻塞任务；说明 Context7 未能确认的部分，再按现有 Web Research 路由补查可靠来源。

## 认证

Context7 基础文档查询可无认证使用；需要更高额度时可使用 `ctx7 login` 或 `CONTEXT7_API_KEY`。不要把 Key 写进 Skill、AGENTS.md 或仓库文件。
