# Context7 Node 隔离（按需）

仅在系统 `ctx7` 不可用、业务项目 Node 版本不适合 Context7，或需要让 Agent 在不同项目间获得稳定 `ctx7` 命令时读取本页。

## 原则

- 不要为了 Context7 修改业务项目自己的 Node 版本、锁文件或依赖。
- 本项目推荐 **Node >=20.18.1**；新建独立 Agent 工具环境时优先 **Node 22 LTS**。
- fnm 是推荐隔离方式，不是强制依赖。
- 如果系统已有稳定可用的官方 `ctx7`，直接复用，不要额外增加隔离层。

## 两种隔离安装方式

### A. 独立私有 npm 工具目录（默认推荐）

Context7 安装到业务项目之外的私有 npm 项目中，并固定版本、保留 `package.json + lockfile`。适合长期维护、升级/恢复边界清晰的场景。

安装目标版本前先检查：

```bash
npm view ctx7@<version> engines bin scripts --json
```

再在隔离 Node 下安装明确版本。若已确认该版本不需要 `preinstall/install/postinstall` 等 lifecycle scripts，可使用 `--ignore-scripts`；不要把这个参数机械固定为永久规则。

### B. 安装到 fnm 隔离 Node 的 global npm（简化可选）

如果用户更看重简单，并接受工具随该隔离 Node 环境一起维护，可以直接：

```bash
fnm exec --using=22 -- npm install -g ctx7@<version>
```

采用前必须在隔离 Node 下检查：

```bash
npm prefix -g
npm root -g
```

确认 global 目录确实属于预期隔离环境，而不是业务项目或共享 npm prefix。不能假设 `fnm exec npm install -g` 天然等于完全隔离。

## 同名 `ctx7` wrapper

确有需要时，可以提供 PATH 中稳定的同名 `ctx7` 透明入口。无论采用 A 还是 B，wrapper 都只负责：

- 选择固定 Node 运行时；
- 调用官方 Context7 的**确定程序入口**；
- 完整透传参数及其边界；
- 透传 stdout、stderr 和 exit code。

不要在 wrapper 中实现 query rewrite、Library ID 选择、fallback、缓存、认证或 Web Research 路由。

因为 wrapper 自己也叫 `ctx7`，**不要在内部再次执行依赖当前 PATH 解析的裸 `ctx7`**，避免递归命中自身。程序入口应根据已安装版本的 `bin` 定义与实际安装位置解析。

## 验收

先验证业务项目 Node 未被改变：

```bash
node --version
ctx7 --version
node --version
```

前后 Node 版本必须一致。

再验证：

```bash
ctx7 library "Spring Boot" "OAuth2 Resource Server 配置"
ctx7 docs /spring-projects/spring-boot "配置属性"
ctx7 library react --json
ctx7 whoami
```

并确认：中文/英文/混合参数、空格与引号、JSON、stdout/stderr 和非 0 exit code 都正常。Windows 还应检查 `Get-Command ctx7 -All` 与 `where.exe ctx7` 指向预期入口。

更完整的安装、wrapper、升级/恢复/卸载说明见仓库 `docs/CONTEXT7-NODE-ISOLATION.md`。
