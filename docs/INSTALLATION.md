# GWRC 安装、跨项目调用与卸载

## 1. 安装原则

GWRC 的 Python CLI 和 Agent Skills 是两个不同但相关的组件：

- Python 包提供确定性计算和 `gwrc` 命令。
- `~/.agents/skills` 提供 Kimi Code 与 Codex 都能发现的用户级工作流。
- 用户级 CLI 启动器位于 `~/.local/bin`，让其他项目在未激活原 venv 时仍能调用同一个 Python 环境。

`gwrc skills install` 安装实际文件，不修改 PATH、Kimi/Codex 配置或系统配置。项目已有 `.agents/skills` 的源码仓库仍可直接使用项目级 Skills；普通科研用户推荐使用下面的用户级安装。

## 2. 安装 Python 包

在 GWRC checkout 中执行。

Windows Git Bash：

```bash
git clone --branch feature/cross-project-agent \
  https://github.com/ruoyuguan/gw-research-copilot.git
cd gw-research-copilot
git checkout 35f9668a01bc01e496025bbee5d64b62f9f567ae
python -m venv .venv
.venv/Scripts/python -m pip install .
```

Windows PowerShell 将 `.venv/Scripts/python` 换成 `.venv\Scripts\python.exe`。macOS/Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
```

开发者在同一目录改用 `python -m pip install -e ".[dev]"`（Windows 使用对应的 `.venv/Scripts/python`），即可同时安装测试工具。此处只从源码 checkout 安装；不要声称项目已在 PyPI 发布。

## 3. 安装用户级 Skills 和 CLI 启动器

```bash
# Windows Git Bash；macOS/Linux 换成 .venv/bin/gwrc
.venv/Scripts/gwrc skills install --scope user
.venv/Scripts/gwrc skills list --scope user
```

用户级安装只处理以下 GWRC 文件：

```text
~/.agents/skills/gw-literature/SKILL.md
~/.agents/skills/gw-review/SKILL.md
~/.agents/skills/gw-statistics/SKILL.md
~/.agents/skills/gw-theory/SKILL.md
~/.agents/gwrc-install.json
~/.local/bin/gwrc             # POSIX 与 Git Bash
~/.local/bin/gwrc.cmd         # Windows PowerShell/Cmd
```

启动器调用安装时的 `sys.executable -m gwrc`，因此不必在其他项目中激活原 venv。若移动或删除该 Python 环境，需要重新安装启动器。不要先删除旧环境再尝试卸载；应先正常卸载，再迁移环境并重新安装。卸载旧启动器后，重装命令必须调用环境内的绝对路径，例如 `.venv/Scripts/gwrc skills install --scope user`（macOS/Linux 使用 `.venv/bin/gwrc`），不要继续调用刚被删除的启动器。

`gwrc skills list` 检查 manifest、实际文件、内容哈希和 PATH 状态。`installed`、`already_installed`、`incomplete`、`not_installed`、`unmanaged` 和 `partially_uninstalled` 是不同状态；manifest 存在不自动等于可用。

### PATH 要求

默认 `~/.local/bin` 必须在 PATH 中，否则安装会在写入前失败。可任选一种处理：

- 将另一个已在 PATH 中的目录传给 `--bin-dir`；
- 只在当前 shell 临时加入该目录，再执行安装；
- 按自己的操作系统文档永久配置 PATH。

POSIX 当前 shell 示例：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Windows PowerShell 当前会话示例：

```powershell
$env:Path = "$HOME\.local\bin;$env:Path"
```

这些命令只改变当前进程环境。安装器不会替你写入 shell profile 或系统 PATH。

验证 CLI：

```bash
command -v gwrc
gwrc --help
```

PowerShell：

```powershell
Get-Command gwrc
gwrc --help
```

如果指定了自定义 `--bin-dir`，卸载时也必须提供同一个目录，防止误删其他位置的文件。

## 4. 在科研项目中调用

打开自己的项目目录，不必再打开 GWRC 源码仓库。Kimi 和 Codex 官方文档均声明扫描用户级 `$HOME/.agents/skills`，但当前已验证的是文件安装和 CLI 可执行性。**Codex 的真实宿主发现与调用尚待真实宿主验证，不能仅因目录存在就宣称已支持。** Kimi 的维护者工作流已通过，但这不等于 Codex 或未参与开发用户的验收。宿主可能需要新会话或重启。

- Kimi：`/skill:gw-statistics`、`/skill:gw-theory`、`/skill:gw-literature`、`/skill:gw-review`。
- Codex：`$gw-statistics`、`$gw-theory`、`$gw-literature`、`$gw-review`。
- 也允许宿主依据 Skill 描述自动选择，但自动路由不是确定性保证；科研任务应能显式调用。

普通 Python 编程不强制使用 GWRC。`gw-review` 默认禁止自动调用，仍可显式使用。`disableModelInvocation` 只控制自动模型调用，不等于卸载文件、禁用 CLI 或完全不加载插件。

## 5. 项目级安装（可选）

若只希望某个项目携带 Skills：

```bash
gwrc skills install --scope project --root /path/to/research-project
```

这只写入该项目的 `.agents/skills` 和 manifest，不创建用户级启动器，也不写真实 home。使用项目级安装时仍需让某个 GWRC Python 环境中的 `gwrc` 可执行。

`--root` 主要用于隔离测试或明确的项目根目录。它不会把宿主的真实 home 改成该路径；不要把临时 root 中的文件安装误称为宿主已经实际发现。

## 6. 卸载与修改保护

```bash
gwrc skills uninstall --scope user
# 项目级卸载使用 --scope project --root /path/to/research-project
```

- 卸载只删除 manifest 中记录且内容哈希未改变的 GWRC 文件。
- 非 GWRC Skills、用户增加的笔记和修改过的 Skill 不会被删除。
- 有修改时返回 `partially_uninstalled` 和退出码 1，并保留 manifest 说明剩余文件；不会报告完全卸载成功。
- 丢失的文件会记录警告；其他未修改文件仍可正常移除。
- 自定义 `--bin-dir` 必须与原安装一致。缺失或损坏的 manifest 会阻止卸载，不会转而递归删除目录。

## 7. 故障排查

1. `gwrc skills list --scope user --json`：检查实际文件和 `command_available`。
2. 检查 `command -v gwrc`（Bash）或 `Get-Command gwrc`（PowerShell），不要只检查 Markdown 是否存在。
3. 检查安装时使用的 Python 是否仍存在、依赖是否完整：`gwrc doctor`。
4. 启动新的宿主会话；Kimi 的显式形式是 `/skill:...`，Codex 是 `$...`，不要混用。
5. 若卸载报告修改，先人工审查被保留文件，再决定如何迁移或删除，不要强行覆盖。

完整的新项目验收见 `ACCEPTANCE.md`。
