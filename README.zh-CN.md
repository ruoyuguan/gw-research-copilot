# GW Research Copilot (GWRC)

[English](README.md) | **中文**

**早期开发中的科研软件（0.1.0）。** GWRC 为引力波研究提供宿主无关的 Agent 工作流、确定性科学检查和可复现记录。它不是语言模型、自动产生科研真理的工具，也不是 ARC、LISA、TianQin 或任何大学、实验室的官方产品。

首个 MVP 聚焦于协方差与自谱 PSD 检查、一个刻意限制适用范围的 Gaussian Fisher 示例，以及重视证据边界的 Agent Skills。它**不**实现完整的 LISA/TianQin 分析流水线、贝叶斯采样器、DWD 种群模型或完整的 SGWB Fisher 计算器。

## 本地已实现的功能

- `check-cov`：检查矩阵是否有限、是否为方阵、实对称或复 Hermitian，并计算特征值、正半定性、数值秩和条件数。
- `check-psd`：检查一维实值自谱、频率顺序与唯一性、非负性，以及必需的单位和谱约定声明。
- `fisher-demo`：使用固定协方差的合成实值 Gaussian mean model，通过 Cholesky 分解求解，并与解析 Fisher 矩阵比较。
- `doctor`：报告必需与可选依赖、项目 Skills 的静态发现结果和可选 ARC 状态。
- `skills install/list/uninstall`：为用户或项目安装打包的 Skills，检查真实 CLI 可用性，并在卸载时保留被修改或无关的文件。
- 每个科学命令都可以在新的目录中写入 `run.json` 和 `report.md`，记录输入摘要、参数、软件版本、时间戳、结果、警告和失败信息。

合法的奇异协方差不会被静默视为可逆矩阵。数值检查通过并不证明 Gaussian 模型、PSD 定义、探测器响应或科研结论是适当的。

## 与 ARC 的关系

GWRC 是受 [Agent Research Copilot (ARC)](https://github.com/tririver/arc) 启发的独立项目，不是 ARC 的 fork 或官方发行版。ARC、AC Foundation 和 ALC 均由其各自作者以 MIT 许可证发布。

可选的 `arc-metadata` 命令是连接 ARC 公开 `arc-paper get-metadata` CLI 的小型桥接。ARC **不是**数值工具的依赖。本 MVP 尚未集成 domain 构建、模型支持的摘要或 ARC 托管计算工作流。已检查的提交、实际验证行为和限制见 [docs/ARC_INTEGRATION.md](docs/ARC_INTEGRATION.md)。

## 环境要求与安装

需要 Python 3.11 或更高版本，以及 Git。请在仓库根目录创建隔离环境。

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Windows Git Bash：

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

下文命令使用该环境中的 `gwrc` 和 `python`。可以激活环境，或在 Windows 上替换为对应的 `.venv/Scripts/gwrc`、`.venv/Scripts/python` 路径，在 macOS/Linux 上替换为 `.venv/bin/...`。`dev` extra 安装离线测试和构建工具；需要可选符号计算时，改安装 `.[theory,dev]`。

验证安装：

```bash
gwrc --help
gwrc doctor
python -m pytest -q
```

`doctor` 不查询论文服务。未配置可选 ARC 不妨碍本地科学工具工作。

## 跨项目安装 Skills

安装 Python 包后，安装 Skills 和绑定该 Python 环境的启动器：

```bash
gwrc skills install --scope user
gwrc skills list --scope user
```

安装器将四个 Skills 写入 `$HOME/.agents/skills`，并将 CLI 启动器写入 `$HOME/.local/bin`（Windows 还包括 `gwrc.cmd`）。该 bin 目录必须已经在 PATH 中；GWRC 不修改 shell 或宿主配置。随后可以打开独立研究项目，不必复制 Skill 文件或激活原 venv。自定义目录、PATH 故障排查、项目级安装和安全卸载见 [docs/INSTALLATION.md](docs/INSTALLATION.md)。

## 使用合成数据快速开始

`examples/` 中的所有文件和内置 Fisher 示例均为 **synthetic（合成数据）**，不是观测数据或探测器预报。

```bash
gwrc check-cov examples/covariance.json --output-dir runs/covariance-demo
gwrc check-psd examples/psd.json --output-dir runs/psd-demo
gwrc fisher-demo --output-dir runs/fisher-demo
python examples/run_mvp.py --output-dir runs/mvp-demo
```

最后一个命令执行三个 CLI 工作流，检查返回结果与保存的记录，并写入一个简短的运行索引。每个 `--output-dir` 都必须是新目录；GWRC 拒绝覆盖已有运行。未指定该选项时，会在 `runs/` 下创建唯一目录。运行目录默认被 Git 忽略，因为其中可能包含本地路径或科研输入。

科学命令将结果以 JSON 输出，并将记录路径输出到 stderr。退出码为：

- `0`：请求的数值检查或操作通过。
- `1`：科学检查失败，或发生预期的执行/集成失败。
- `2`：命令用法或输入文档错误。

### 输入约定

协方差文件包含数值矩阵：

```json
{"data_origin": "synthetic", "matrix": [[2.0, 0.3], [0.3, 1.0]]}
```

PSD 文件提供数组和声明；完整示例见 `examples/psd.json`。必需字段为 `frequency`、`psd`、`frequency_unit`、`psd_unit`、`psd_definition` 和 `spectral_convention`（`one-sided` 或 `two-sided`）。`frequency_order` 默认为 `increasing`，也可为 `decreasing` 或 `unordered`。可选 `fourier_convention` 会被保留以供审查。

GWRC 不推断单双边 PSD 转换因子或 Fourier 归一化。双边谱允许负频率，单边谱拒绝负频率。定义、容差和适用范围见 [docs/SCIENTIFIC_CONVENTIONS.md](docs/SCIENTIFIC_CONVENTIONS.md)。

Fisher 示例使用实值数据的 `y ~ N(J theta, C)`，其中 `C` 为固定实对称正定矩阵：

```text
J = [[1, 0], [1, 1], [0, 1]]
C = diag(4, 1, 1)
F = J^T C^-1 J = [[5/4, 1], [1, 2]]
```

该示例不包含参数相关协方差项、复数似然、多通道 inner product 或探测器响应模型。

## Agent Skills 与宿主支持

仓库提供四个目录形式的 Skills：

- `gw-literature`：基于来源的阅读，并明确处理文献服务不可用的情况。
- `gw-theory`：约定、单位、推导检查、近似条件，以及独立代数或数值检查。
- `gw-statistics`：PSD、协方差、Gaussian likelihood 假设、Fisher 限制和可复现 CLI 使用。
- `gw-review`：显式、轻量的结果与证据复核；不自动进行多 Agent 并行调用。

### Kimi Code

`.agents/skills/<name>/SKILL.md` 的布局和 frontmatter 遵循 [Kimi 官方 Skills 文档](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html)。本 MVP 在 Windows 开发过程中，Kimi Code 发现了项目 Skills，并展开了对 `gw-statistics` 和 `gw-literature` 的直接 Skill 工具调用。这验证了该环境中的发现和直接加载，不保证所有自动路由或斜杠命令路径。打开 Git 仓库根目录并启动新会话，以扫描项目 Skills。测试套件验证其静态结构，不证明模型总会选择预期 Skill。

自动调用受各 Skill 的领域描述限制。明显的引力波统计、理论或文献任务可以选择相应工作流；普通 Python 或一般编程不强制使用 GWRC。

在 Kimi 聊天中显式调用（不是在 shell 中）：

```text
/skill:gw-statistics
/skill:gw-theory
/skill:gw-literature
/skill:gw-review
```

如需禁止某个 Skill 的自动调用，可编辑本仓库中的 frontmatter：

```yaml
disableModelInvocation: true
```

修改 Skill 配置后启动新会话。该字段禁止自动模型调用，但仍可显式 `/skill:` 使用；它**不等于**禁用插件或卸载所有 GWRC 代码。`gw-review` 默认仅手动调用。若要完全不加载项目 Skills，可在此 checkout 之外运行宿主，或使用不含 `.agents/skills` 的 checkout；GWRC 不修改全局 Kimi 配置。

### Codex、Claude Code 与其他宿主

Python CLI 独立于 Agent 宿主，Skill 文件采用可移植的 Markdown/YAML 约定。[Codex 官方 Skills 文档](https://developers.openai.com/codex/skills)将 `$HOME/.agents/skills` 列为用户级目录。维护者在 Windows 上使用 `codex-cli 0.162.0-alpha.17.2` 测试时，初次发现沙箱无法执行已安装的 Microsoft Store Python。换用隔离的标准 CPython 3.12.15 环境并绑定启动器后，后续用户级 `$gw-statistics` 在 `workspace-write` 下完成合法和故意非法输入检查，退出码符合预期，`run.json`/`report.md` 经核验且输入未改变。这只验证该特定环境中的 Codex CLI 工作流，不证明所有 Python 发行版。

本版本尚未实际测试 VS Code Codex 图形界面和 Claude Code。CLI 结果不证明原生 IDE 集成，也不等于独立研究人员验收。初次失败与后续成功记录见 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。完成真实宿主 smoke 后再考虑宿主专用打包。数值工具本身不选择模型账号、付费 API 或模型供应商。

## 可选 ARC 元数据桥接

按照 ARC 官方说明和固定来源单独安装 ARC。然后将 `arc-paper` 放入 PATH，或通过 `GWRC_ARC_PAPER` 指定其可执行文件：

```bash
export GWRC_ARC_PAPER=/path/to/arc-paper
gwrc doctor --json
gwrc arc-metadata arXiv:0911.3380 --output-dir runs/arc-metadata-demo
```

Windows 上使用对应环境的 `arc-paper.exe` 路径和 shell 的环境变量语法。使用官方 launcher 时，改设 `GWRC_ARC_RUNTIME`；runtime 探测仅调用只读 `arc-runtime doctor`，不触发安装。成功的元数据操作可能使用 ARC 缓存或论文服务，本身不构成文献评议。

**当前验证状态：**官方 ARC runtime 已在 WSL2 Ubuntu 中完成元数据、目录、全文检索和章节读取，`GWRC_ARC_RUNTIME` 适配也已通过。原生 Windows CLI 探测可用，但原生 Windows 元数据读取仍受已复现的上游 `ac-jobs` 文件锁释放错误阻塞。数值工具不受影响。确切提交、证据和不支持的工作流见 [docs/ARC_INTEGRATION.md](docs/ARC_INTEGRATION.md)。离线测试不要求 ARC。

## 开发与项目结构

```text
.agents/skills/       面向宿主的科研工作流
src/gwrc/core/       共享验证、错误和严格 JSON 处理
src/gwrc/tools/      确定性协方差、PSD 和 Fisher API
src/gwrc/cli/        公共命令语法
src/gwrc/integrations/ 可选外部服务适配器
src/gwrc/reporting/  JSON 和 Markdown 运行记录
tests/               离线自动化测试
examples/            合成输入和端到端运行器
docs/                架构、科学约定和维护文档
.github/             CI、Dependabot 和协作模板
```

提交改动前运行常规检查：

```bash
python -m ruff check src tests examples
python -m pytest -q
python -m pip check
python -m build
```

参见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)、[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 和 [docs/ROADMAP.md](docs/ROADMAP.md)。贡献流程遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的 feature branch + pull request 工作方式。

## 贡献者与 AI 辅助开发

本阶段实现使用了 VS Code 中的 Kimi Code 扩展。维护者提供的开发配置为 **K3.1 Pro，Thinking effort: Max**。人类维护者、AI 辅助实现和 Codex CLI 辅助验证的具体角色见 [CONTRIBUTORS.md](CONTRIBUTORS.md)。

这些记录用于披露开发过程，不构成法律作者身份或版权归属的指定，也不代表 AI 输出自动具备科研正确性。人类维护者仍负责审查、测试证据、科学解释和发布决定。

## 许可证与科学免责声明

GWRC 按 [MIT License](LICENSE) 发布。本早期版本不提供任何保证。用户必须独立核验科学假设、来源主张、数值稳定性和物理意义。本项目不暗示任何引力波合作组织或学术机构的认可。
