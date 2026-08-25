# 更新 Agent Web Research

本项目的 Direct/手工安装采用“**以当前仓库为准重新同步**”的轻量更新方式，不需要知道旧版本号，也不维护逐版本迁移清单。

## 推荐流程

先获取仓库最新代码，然后预览更新：

```bash
python scripts/install.py --project-root <PROJECT_ROOT> --update --dry-run
```

确认无误后执行：

```bash
python scripts/install.py --project-root <PROJECT_ROOT> --update
```

最后验证：

```bash
python scripts/verify.py --project-root <PROJECT_ROOT>
```

## `--update` 会做什么

- `web-research-router`、`exa-retrieval`、`context7-tech-docs`：以当前仓库版本为准，整体新增或替换。
- `AGENTS.md`：如果已存在 `web-research-router` 受管 marker，只更新 marker 内的路由提示；如果没有 marker，不猜测、不自动追加，只给出提示。
- `web-searcher.toml`：默认保留项目现有文件，并生成/刷新 `web-searcher.agent-web-research.candidate.toml` 供比较。
- Context7：只检查官方 `ctx7` CLI 是否可用，不自动修改 Node/fnm/项目运行环境。

如果确认项目中的 `web-searcher.toml` 没有需要保留的定制，可以显式覆盖：

```bash
python scripts/install.py --project-root <PROJECT_ROOT> --update --replace-agent
```

## 如果 AGENTS.md 没有受管 marker

旧的手工安装可能只是把一段 Web Research 说明直接写进 `AGENTS.md`，没有：

```text
<!-- web-research-router:start -->
...
<!-- web-research-router:end -->
```

这种情况 updater 不会尝试猜测哪一段旧文字应该删除。

建议先让项目 AI/用户人工清理旧的同义提示，然后执行一次：

```bash
python scripts/install.py --project-root <PROJECT_ROOT> --update --patch-agents
```

它会加入受管 marker。此后再更新时，只需 `--update` 即可自动刷新该区块。

## 非默认路径或路由风格

本项目不保存安装状态，因此不会猜测团队以前选择过的自定义目录。

如果旧安装使用了非默认 `--skills-dir`、`--agents-dir`、`--agents-file`，更新时继续传入相同参数即可。

`--update` 默认按 `skill` 路由风格同步。如果项目明确使用 `inline` 或 `file` 风格，请继续带上原来的参数，例如：

```bash
python scripts/install.py \
  --project-root <PROJECT_ROOT> \
  --update \
  --routing-style file \
  --rules-dir docs/agent-rules
```

`file` 风格下，`web-research-router.md` 也会以当前仓库版本为准同步。

## Plugin 安装

`--update` 只用于 Direct/手工安装。通过 Codex Plugin 安装的用户应使用 Codex 自己的 Plugin 管理机制更新插件。

## 给项目 AI 的最短指令

```text
请按本仓库 UPDATING.md 更新当前项目中的 Agent Web Research。
先执行 --update --dry-run；确认目标路径和变更合理后再执行正式 --update，并运行 scripts/verify.py。
Skill 以当前仓库为准同步；AGENTS 只修改受管 marker；已有 web-searcher 默认保留并检查 candidate。
如果项目以前使用了自定义安装路径或 routing style，沿用原参数，不要自行猜测新路径。
```
