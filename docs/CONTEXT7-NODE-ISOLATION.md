# Context7 Node 隔离与 `ctx7` 稳定入口

本文只解决一个问题：**当业务项目的 Node.js 版本与 Context7 CLI 的运行环境冲突时，如何给 Agent 提供稳定、透明的 `ctx7` 命令，而不改变业务项目 Node 环境。**

Context7 CLI 顶层包当前仍声明 Node.js `>=18`，但其生态中的新依赖已经明显转向 Node 20+，当前 Context7 MCP package 也已经要求 Node `>=20.18.1`。为了降低长期工具环境的兼容风险，本项目：

- **最低推荐基线：Node >=20.18.1**；
- **优先：Node 22 LTS**，用于独立的 Agent 工具环境；
- 如果系统里已经有可工作的官方 `ctx7`，直接使用即可，不需要为了本插件额外创建隔离环境。

## 1. 目标与职责边界

- 不为 Context7 修改业务项目自己的 Node.js 版本、版本文件、锁文件或依赖。
- fnm 等 Node.js 版本管理器只负责提供固定运行时，不承担 Context7 的查询或路由逻辑。
- Agent 最终只依赖 PATH 中稳定的同名 `ctx7` 命令。
- wrapper 只负责选择固定运行时、调用官方 Context7 程序入口，并透传参数、stdout、stderr 与 exit code。
- wrapper 不实现 query rewrite、Library ID 选择、缓存、认证或 Web Research 路由。

推荐链路：

```text
用户执行 ctx7
  -> 用户级命令目录中的同名 wrapper（仅隔离场景需要）
  -> fnm 选择固定 Node.js
  -> 官方 Context7 CLI 的确定程序入口
  -> Context7 服务
```

## 2. 什么时候需要隔离

典型情况：

```text
业务项目 → Node 14/16/18 或其它锁定版本
Context7 工具环境 → Node 20.18.1+，推荐 Node 22 LTS
```

如果当前 `ctx7` 已经在业务项目之外稳定工作，就不要为了“更标准”再增加隔离层。

需要隔离时，本项目提供两种方式：

1. **独立私有 npm 工具目录（默认推荐）**：Context7 程序、精确版本和锁文件与 Node 运行时进一步解耦，适合长期维护。
2. **直接安装到 fnm 隔离 Node 的全局 npm 目录（简化可选）**：配置更少，适合用户明确接受工具跟随该 Node 环境生命周期的场景。

两种方式都不能改变业务项目自己的 Node 环境。

## 3. 先检查目标 Context7 包

不要把某个历史版本的要求当成永久事实。先选择准备安装的 Context7 版本，并在目标隔离 Node 下检查：

```bash
npm view ctx7@{{ctx7-version}} engines bin scripts --json
```

重点确认：

- `engines.node`；
- `bin` 中实际的 `ctx7` 程序入口；
- 是否声明 `preinstall` / `install` / `postinstall` 等安装生命周期脚本。

如果目标版本没有必要的安装生命周期脚本，可优先使用 `--ignore-scripts` 降低安装副作用；如果未来版本确实依赖安装脚本，应先审查用途，再决定是否允许执行，不要机械固定 `--ignore-scripts`。

## 4. 方案 A：独立私有 npm 工具目录（默认推荐）

长期维护的 Agent CLI 优先安装到独立私有 npm 项目，而不是业务项目或共享全局 npm 目录。

优点：

- Context7 的升级、降级、恢复和卸载边界清楚；
- `package.json` 与 lockfile 能记录精确版本和完整依赖；
- 不受用户 npm 全局 prefix 和其它 Node 工具影响；
- 更换或重装隔离 Node 运行时后，工具目录仍可依据 lockfile 恢复；
- 多个 Agent 工具不会共同堆积在某个 Node 版本的 global package 空间。

先确定这些语义变量，不把某台机器路径写成通用事实：

```text
{{node-version}}       固定的 Node.js 版本（推荐 22 LTS）
{{tool-runtime-dir}}   Context7 独立工具目录
{{user-command-dir}}   已加入用户 PATH 的命令目录
{{fnm-executable}}     fnm 可执行文件
{{ctx7-entry}}         独立目录内官方 ctx7 程序入口
{{ctx7-version}}       准备固定安装的 Context7 版本
```

建立工具目录并固定安装版本：

```bash
cd {{tool-runtime-dir}}
npm init -y
npm pkg set private=true --json
npm install --save-exact ctx7@{{ctx7-version}}
```

如果前面的 `npm view ... scripts` 已确认目标版本不需要安装生命周期脚本，可改用：

```bash
npm install --save-exact --ignore-scripts ctx7@{{ctx7-version}}
```

上述 npm 命令必须在选定的隔离 Node.js 下运行。使用 fnm 时可通过：

```bash
fnm exec --using={{node-version}} -- npm ...
```

Windows 下如果 npm 解析为命令脚本（`.cmd`），可显式通过：

```text
fnm exec --using={{node-version}} -- cmd.exe /d /c npm ...
```

安装完成后确认：

- `package.json` 是私有工具项目，并记录精确 Context7 版本；
- lockfile 已生成；
- 根据该版本 `bin` 定义解析出的 `{{ctx7-entry}}` 实际存在；
- 安装目录不在业务项目或共享 global npm 目录内；
- 安装期间没有未经审查的额外副作用。

## 5. 方案 B：直接安装到 fnm 隔离 Node 的全局 npm 目录（简化可选）

如果用户更看重简单，且明确接受 Context7 随该隔离 Node 环境一起升级、删除或重建，可以直接安装到该 Node 的 global npm 目录。

例如：

```bash
fnm install 22
fnm exec --using=22 -- npm install -g ctx7@{{ctx7-version}}
```

Windows 下可按实际命令解析情况使用：

```text
fnm exec --using=22 -- cmd.exe /d /c npm install -g ctx7@{{ctx7-version}}
```

采用此方案前必须在隔离 Node 下检查：

```bash
npm prefix -g
npm root -g
```

确认 global prefix/root 确实属于预期隔离环境，而不是：

- 业务项目目录；
- 用户自定义的共享 npm prefix；
- 其它 Node 工具共用且不希望被 Context7 生命周期影响的目录。

如果 global prefix 不符合预期，应改用方案 A，而不是继续假设“`fnm exec npm install -g` 一定已经隔离”。

此方案更简单，但应接受这些取舍：

- 删除/重装对应 fnm Node 版本时，global Context7 可能需要重装；
- 不像方案 A 那样天然拥有项目级 `package.json + lockfile` 恢复边界；
- 多个全局工具可能共享该 Node 环境的 global package 空间。

## 6. 用户级同名 `ctx7` wrapper

无论采用方案 A 还是 B，如果需要让 Agent 在不同业务项目中始终只执行：

```bash
ctx7 ...
```

可以在已经加入用户 PATH 的命令目录中建立透明同名 wrapper。

不要为了 Context7 把隔离 Node 的整个安装目录长期放到业务终端 PATH 前部。

wrapper 必须固定：

- `fnm` 可执行文件；
- Node 版本；
- 官方 Context7 的**确定程序入口** `{{ctx7-entry}}`。

Windows `.cmd` 可使用下面的通用结构：

```batch
@echo off
setlocal
set "FNM_EXE={{fnm-executable}}"
set "CTX7_ENTRY={{ctx7-entry}}"

if not exist "%FNM_EXE%" (
  echo fnm.exe was not found: "%FNM_EXE%" 1>&2
  exit /b 1
)

if not exist "%CTX7_ENTRY%" (
  echo Pinned Context7 CLI was not found: "%CTX7_ENTRY%" 1>&2
  exit /b 1
)

"%FNM_EXE%" exec --using={{node-version}} -- node "%CTX7_ENTRY%" %*
exit /b %ERRORLEVEL%
```

wrapper contract：

- 固定 Node.js 版本和官方 Context7 程序入口；
- 完整透传参数及其边界、stdout、stderr 和 exit code；
- 入口缺失时立即失败并给出可定位错误；
- 不实现查询改写、Library ID 选择、缓存、认证或 Web Research 路由；
- **不在内部再次执行依赖当前 PATH 解析的裸 `ctx7`**，避免递归命中 wrapper 自身。

`{{ctx7-entry}}` 应在安装时依据目标版本的 `bin` 定义和实际安装位置解析，不要长期假设某个固定目录结构永远不变。

## 7. 验收

先证明业务项目运行时没有被改变：

```bash
node --version
ctx7 --version
node --version
```

前后两次业务 Node.js 版本必须一致。

随后至少验证：

```bash
ctx7 library "Spring Boot" "OAuth2 Resource Server 配置"
ctx7 docs /spring-projects/spring-boot "配置属性"
ctx7 library react --json
ctx7 whoami
```

还应补充一次非法命令或无效参数，确认 stderr 和非零 exit code 没有被 wrapper 吞掉。

Windows 环境同时验证：

- 加载和不加载 PowerShell 用户配置时都能解析同一个受管命令；
- 中文、英文、中英混合、空格和引号参数保持完整；
- `--json` 输出没有混入 wrapper 日志；
- `Get-Command ctx7 -All` 与 `where.exe ctx7` 均指向预期用户级入口。

如果官方 `ctx7` 在当前环境已经全部通过这些测试，就不要额外增加 wrapper。

## 8. 升级、恢复与卸载

### 方案 A

升级只在独立工具目录中安装明确版本：

```bash
npm install --save-exact ctx7@{{new-version}}
```

如果目标版本已审查并适合禁止 lifecycle scripts，可加 `--ignore-scripts`。

恢复优先依据已确认的 lockfile：

```bash
npm ci
```

同样，只有在依赖脚本已经核实不需要时才使用 `npm ci --ignore-scripts`。

### 方案 B

升级只针对 fnm 隔离 Node 的 global npm：

```bash
fnm exec --using={{node-version}} -- npm install -g ctx7@{{new-version}}
```

升级前后重新确认 `npm prefix -g`、`ctx7 --version` 和 wrapper 的确定入口仍然正确。

### 卸载

只处理 Context7 自己的安装位置和用户级 wrapper。删除前按当前环境的破坏性操作规则确认精确目标；不要顺带删除业务项目 Node、共享 Node runtime 或其它工具。

## 9. 常见错误

- 为使用 Context7 升级或切换业务项目 Node.js。
- 把“独立私有 npm 工具目录”误解为强制要求；如果 fnm global prefix 已确认隔离且用户接受其生命周期，方案 B 也是有效选择。
- 未核对 `npm prefix -g` 就认为 `fnm exec npm install -g` 一定完成了隔离。
- 把多个长期工具都安装进一个并非预期的共享 global npm 目录。
- 使用 `npx ...@latest` 作为长期稳定入口，导致每次运行可能下载或变化。
- wrapper 内部再次执行裸 `ctx7`，形成递归或依赖不稳定的 PATH 顺序。
- 只验证 `ctx7 --version`，没有验证真实查询、JSON、参数边界、stderr、exit code，以及业务 Node.js 保持不变。

Context7 查询本身仍遵从 `context7-tech-docs` Skill 的版本选择、认证安全、查询次数和 Web Research 回退边界；本文只负责 Node.js 与命令入口隔离。
