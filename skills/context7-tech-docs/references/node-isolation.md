# Context7 Node 隔离（按需）

仅在系统 `ctx7` 不可用、业务项目 Node 版本过旧，或需要让 Agent 在不同项目间获得稳定 `ctx7` 命令时读取本页。

## 推荐基线

- 不要为了 Context7 修改业务项目自己的 Node 版本。
- Context7 顶层文档仍可能标注 Node `>=18`，但当前依赖生态已明显转向 Node 20+；本项目推荐 **Node >=20.18.1**。
- 新建独立 Agent 工具环境时，优先 **Node 22 LTS**。
- fnm 是推荐隔离方式，不是强制依赖。

## 基本流程

```bash
fnm install 22
fnm exec --using=22 npm install -g ctx7@latest
fnm exec --using=22 ctx7 --version
```

如果直接执行隔离环境中的 `ctx7` 已经稳定，就不需要 wrapper。

## 同名 `ctx7` wrapper

确有需要时，可以提供 PATH 中稳定的同名 `ctx7` 透明入口。它只负责进入固定 Node 环境并调用**官方 ctx7 CLI**，同时完整透传：

- 参数及其边界；
- stdout；
- stderr；
- exit code。

不要在 wrapper 中实现 query rewrite、Library ID 选择、fallback、缓存、认证或 Web Research 路由。

因为 wrapper 自己也叫 `ctx7`，不要在内部简单再次执行依赖当前 PATH 解析的裸 `ctx7`，避免某些 PATH 顺序下递归命中自身。应确认进入隔离 Node 环境后调用的是该环境中的官方 ctx7 确定入口。

## 验收

至少验证：

```bash
ctx7 --version
ctx7 library "Spring Boot" "OAuth2 Resource Server 配置"
ctx7 docs /spring-projects/spring-boot "配置属性"
ctx7 library react --json
ctx7 whoami
```

确认中文、英文、中英混合、空格/引号参数、JSON、stdout/stderr 和非 0 exit code 均正常。
