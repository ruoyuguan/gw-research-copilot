# 开发与维护

## 1. 本地环境

要求 Python 3.11+、Git。项目使用 `src/` 布局和 Hatchling，运行依赖仅 NumPy/SciPy；ARC 不随核心安装。

Windows Git Bash：

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

macOS/Linux 将 `.venv/Scripts/python` 换成 `.venv/bin/python`，PowerShell 使用 `.venv\Scripts\python.exe`。理论 Skill 可按需使用 `.[theory,dev]` 安装 SymPy，但核心数值测试不依赖它。

## 2. 常规检查

```bash
python -m ruff check src tests examples
python -m pytest -q
python -m pip check
gwrc --help
gwrc doctor --json
gwrc skills list --scope user
python examples/run_mvp.py --output-dir runs/development-mvp
bash -n scripts/validate_arc_linux.sh
python -m build
```

每次演示必须使用新目录。不要删除他人运行记录来规避覆盖保护，换一个输出目录即可。默认测试离线，不需要 ARC、API key 或模型账户。

构建 wheel 后，应在新的检查环境中安装该 wheel 并再次执行测试和 CLI smoke，而不是只验证 editable install：

```bash
python -m venv .venv-wheel-check
# Windows Git Bash；其他系统调整 Scripts/bin 路径
.venv-wheel-check/Scripts/python -m pip install dist/gw_research_copilot-0.1.0-py3-none-any.whl \
  "pytest>=8,<9" "PyYAML>=6,<7"
.venv-wheel-check/Scripts/python -m pytest -q
.venv-wheel-check/Scripts/gwrc fisher-demo --output-dir runs/wheel-fisher
```

## 3. 修改科学工具

1. 先写数据类型、矩阵维度、统计假设、适用范围和参考结果。
2. 将数组/数学检查放在 `tools`，文件与进程处理放在 CLI 或 adapter。
3. 给公共 API 添加类型和 docstring。使用稳定消息代码，保留警告而不是隐藏边界输入。
4. 测试合法、奇异/病态、非有限、形状和约定错误；禁止用同一实现的输出充当唯一参考。
5. 同步科学约定、README、Skill 和运行记录参数。删除或改写描述旧行为的注释与文档。
6. 实际执行相关 CLI 和端到端示例，不能仅凭 import/compile 声称可用。
7. 保持 `--help`、`doctor` 和 Skills 管理命令轻量，不在 CLI 顶层加载 NumPy/SciPy；科学处理函数和 `RunRecorder` 按需加载，并用启动路径测试防止回归。

绝对容差与被检查量同单位；相对容差无量纲。不要把 PSD 容差、Hermitian 容差和数值秩容差混为一个不可解释的 `epsilon`。

## 4. ARC 开发

锁定提交、公开接口和当前验证状态见 `ARC_INTEGRATION.md`。上游调研与独立 ARC 环境放在被忽略的 `.local/`，不得把其 `.git` 历史或整个源码树合入 GWRC。

adapter 只使用公开 CLI/Python API，检查版本/信封、退出码和错误。缺失、不可用和已验证可用必须不同。不得创建永远返回成功的生产 mock backend。测试中的传输替身只验证 GWRC 错误处理。

真实联网 smoke 使用公开文献、有限次数和独立输出目录。不得上传私人论文、组内笔记、令牌或受限合作资料。联网失败不阻塞离线测试，也不得把失败改写成集成成功。

### Linux ARC 验证

准备固定 commit 的 ARC/AC checkout 和经校验的 Linux uv 后，在 WSL 或原生 Linux 执行：

```bash
AC_INSTALL_UV=/path/to/verified/linux/uv bash scripts/validate_arc_linux.sh
```

脚本检查固定 commit，使用 WSL 原生 `/tmp` 创建新 runtime、venv 和缓存，不需要 sudo。Windows 挂载源码只用于创建原生 checkout；Git `safe.directory` 和换行差异只在当前命令中处理，不修改全局配置。公开论文的 metadata、目录、全文检索、章节及 GWRC runtime 适配都必须通过结构化检查。

精简证据复制到 Git 忽略的 `.local/verification/arc-linux-*`，不依赖 `/tmp` 在后续调用中持久存在。默认 CI 不访问文献服务；手动 Ubuntu smoke 与离线回归分开。

## 5. 分支、提交与发布

采用 feature branch + PR。保持改动聚焦，提交前审查 `git diff`、暂存清单和测试证据；不要自动提交运行产物。发布版本、依赖范围或许可证变更应在 PR 中清楚说明。

首次公开及之后新增文件时检查 `.gitignore`、敏感信息和完整历史。优先用 Gitleaks 扫描暂存区和历史，并进行人工复核。仅删除工作区中的秘密不能清理历史，发现泄露后必须轮换凭据并清除所有公开历史。

## 6. 文档与社区

科学/架构文档主要使用中文，README 和国际社区文件使用英文。公共声明必须反映已实际验证的能力。Codex、Claude Code 或 Kimi 的原生支持只有在对应宿主实测后才能声明。

不要创建无职责的目录、空后端或未实现的“完整平台”入口。路线图是计划，不是当前功能列表。
