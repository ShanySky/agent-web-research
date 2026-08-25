# Context7 Node 隔离与 `ctx7` 稳定入口

本文只解决一个问题：**当业务项目的 Node.js 版本与 Context7 CLI 要求冲突时，如何给 Agent 提供稳定、透明的 `ctx7` 命令，而不改变业务项目 Node 环境。**

Context7 官方 CLI 当前要求 Node.js `>=18`。如果系统里已经有可工作的官方 `ctx7`，直接使用即可；不需要为了本插件额外创建隔离环境。

## 什么时候需要隔离

典型情况：

```text
业务项目 → Node 14/16 或固定旧版本
Context7 CLI → Node >=18
```

不要为了 Context7 修改项目自己的 Node 版本、锁文件或运行环境。可使用 fnm（推荐但非强制）创建独立 Agent 工具环境。

## 推荐思路

```text
Agent / Skill
    ↓
ctx7
    ↓
透明 wrapper（仅需要隔离时）
    ↓
固定的 fnm Node 环境
    ↓
官方 ctx7 CLI
```

wrapper 仍然叫 `ctx7`。它不是另一个 Context7 客户端，只是官方 CLI 的稳定入口。

## 建立独立 Node 环境

下面以 Node 22 为示例；实际可使用任意满足 Context7 要求并适合本机的稳定版本。

```bash
fnm install 22
```

在该版本环境中安装官方 CLI：

```bash
fnm exec --using=22 npm install -g ctx7@latest
```

先直接验证：

```bash
fnm exec --using=22 ctx7 --version
fnm exec --using=22 ctx7 library react "useEffect cleanup"
```

> fnm 的具体参数可能随版本变化。实施时应先运行 `fnm --help` / `fnm exec --help` 核对本机版本，不要机械依赖本文示例。

## 同名 `ctx7` wrapper 的要求

如果需要让 Agent 在任何项目 Node 环境下都只执行 `ctx7 ...`，可以在 PATH 较高优先级的位置建立透明 wrapper。

wrapper 只允许负责：

- 调用固定的 fnm Node 环境；
- 完整透传所有参数，包括带空格参数；
- stdout 原样透传；
- stderr 原样透传；
- 返回官方 `ctx7` 的 exit code。

wrapper 不应负责：

- query rewrite；
- Library ID 选择；
- Context7 fallback；
- Web Research 路由；
- 查询缓存；
- API Key 管理。

## Windows 示例思路

Windows 上建议优先使用一个很薄的 `.cmd` 或 PowerShell wrapper，并把它放到专门的 Agent tools PATH 目录。不要修改业务项目的 Node 配置。

伪代码逻辑：

```text
接收全部参数
→ fnm exec --using=<isolated-node> ctx7 <全部原始参数>
→ 透传 stdout/stderr
→ exit <ctx7 exit code>
```

不要在 wrapper 内拼接用户 query 成单个字符串后再次解析；要保持参数边界，避免空格、引号、中文被破坏。

## 验收清单

创建 wrapper 后至少验证：

```bash
ctx7 --version
ctx7 library "Spring Boot" "OAuth2 Resource Server 配置"
ctx7 docs /spring-projects/spring-boot "配置属性"
ctx7 library react --json
ctx7 whoami
```

并确认：

- 中文 query 正常；
- 英文 query 正常；
- 中英文混合正常；
- 带空格参数正常；
- JSON 输出正常；
- stdout/stderr 不乱码；
- 非 0 exit code 能原样返回。

如果官方 `ctx7` 在当前环境已经全部通过这些测试，就不要额外增加 wrapper。

## 认证

Context7 文档查询可无认证使用。需要更高额度时，可使用：

```bash
ctx7 login
```

或环境变量 `CONTEXT7_API_KEY`。凭证不要写入项目仓库、Skill 或 AGENTS.md。
