# GWRC 用户验收与证据分级

## 1. 验收目标

目标用户在自己的项目中完成一次自然语言科学检查：发现或显式调用 `gw-statistics`，读取正确输入，执行确定性工具，保存运行记录，并解释科学局限。

本文件区分三类证据，不能相互替代：

1. **自动化工程验证**：离线测试、wheel、安装器、Bash/PowerShell 和独立目录检查。
2. **维护者真实宿主 smoke**：在实际 Kimi/Codex VS Code 中执行下面的任务。
3. **未参与开发的组员验收**：由一名新用户按照文档独立完成。只有这一类证据满足最终 v0.2.0 用户验收目标，不能由开发者脚本或模型自我声明替代。

默认 pytest 不调用模型。真实宿主 smoke 使用测试者已有账户，可能消耗额度，应限制为一个任务并与离线 CI 分开。

## 2. 准备独立研究项目

本清单对应的验收提交为 `35f9668a01bc01e496025bbee5d64b62f9f567ae`。不要使用尚未包含候选安装功能的旧 `main`：

```bash
git clone --branch feature/cross-project-agent \
  https://github.com/ruoyuguan/gw-research-copilot.git
cd gw-research-copilot
git checkout 35f9668a01bc01e496025bbee5d64b62f9f567ae
```

先按 `INSTALLATION.md` 安装 Python 包并执行 `gwrc skills install --scope user`。然后使用合成示例创建独立项目，避免父目录 GWRC 的项目 Skills 掩盖用户级安装：

```bash
# 在 GWRC checkout 中
mkdir -p .local/acceptance
cp -r examples/research_project .local/acceptance/research-project
cd .local/acceptance/research-project
git init -b main
```

所有数据均为 synthetic，不是 LISA、TianQin 或观测数据。`.local/` 中的测试项目、运行记录和模型输出不进入公开仓库。

检查：

```bash
gwrc skills list --scope user
command -v gwrc
python analysis.py
```

PowerShell 用 `Get-Command gwrc` 替代第二条命令。`analysis.py` 应报告 `one-sided`、4 个频率点、2×2 协方差，并明确不做谱约定转换或独立性假设。

## 3. 执行真实宿主任务

在独立项目根目录打开新的 VS Code 窗口或新宿主会话。Kimi 使用 `/skill:gw-statistics`，Codex 使用 `$gw-statistics`，然后输入：

> 请检查这个项目的 PSD 和协方差定义。先读取 analysis.py 和 data/，运行合适的确定性工具，保存记录并解释科学局限。

可另行测试不显式命名 Skill 的自动识别，但显式调用是基本验收路径；自动路由不是确定性要求。宿主若修改运行参数或输出目录，应保持原输入和数学约定，不得为了得到通过结果而修改数据。

## 4. 验收判据

必须同时满足：

- Agent 实际读取 `analysis.py`、`data/psd.json` 和 `data/covariance.json`，而非只给通用解释。
- 调用 PATH 中真实的 `gwrc check-psd` 与 `gwrc check-cov`，或明确等价的公开 Python API。
- 两个命令退出码均为 0，结果显示 PSD 和协方差检查通过。
- 在新的输出目录生成 `run.json` 和 `report.md`，且 `status=completed`；输入 digest、参数和软件版本可读取。
- Agent 明确说明数据是 synthetic，单边 PSD 声明只是用户提供的约定，工具没有证明其估计过程或单位物理意义。
- Agent 区分数值检查通过、统计模型假设和物理结论；不得声称已建立 Gaussian likelihood、通道独立性或完整探测器模型。
- 输出中没有伪造文献、观测、参数估计或 ARC 成功状态。

直接检查命令可作为故障时的对照，但不能代替 Agent 工作流：

```bash
gwrc check-psd data/psd.json --output-dir runs/direct-psd
gwrc check-cov data/covariance.json --output-dir runs/direct-covariance
```

每次运行使用新目录，不能覆盖旧记录。

### 负例与解释边界

补充检查 `data/invalid_psd.json`（重复频率和负 PSD）以及 `data/invalid_covariance.json`（非 Hermitian 矩阵）。这些也是 synthetic，不是用于强迫通过测试的合法样本：

```bash
gwrc check-psd data/invalid_psd.json --output-dir runs/invalid-psd
gwrc check-cov data/invalid_covariance.json --output-dir runs/invalid-covariance
```

正确行为是退出码 1、`valid=false`，并报告 `duplicate_frequency`、`negative_psd` 或 `not_hermitian` 等具体错误。`status=completed` 仅表示诊断执行结束，不表示科学检查通过。Agent 不得修改输入以消除错误，也不得把非法矩阵解释成正定、把非法 PSD 解释成有效物理谱，或声称这些错误证明更广泛的物理模型成立。

## 5. 记录证据

为维护者 smoke 和外部组员分别记录：

- 测试者角色（维护者或未参与开发的组员），无需披露个人敏感信息。
- GWRC commit 或 wheel 版本、操作系统、宿主及扩展版本。
- 用户级安装和 PATH 检查结果。
- 实际提示、Skill 调用形式、真实 CLI 命令及退出码。
- `run.json`/`report.md` 路径和人工核对结果。
- 科学限制是否被正确解释。
- 成功、部分成功或失败，以及最小复现和未解决问题。

公开反馈不得包含账号令牌、私有研究资料、未发表论文、受限合作数据或含个人信息的日志。维护者 smoke 通过不等于新组员验收通过；没有实际组员证据时，该事项保持未完成。

## 6. 常见问题

- **只有源码仓库中的 Skill 被发现**：确认测试项目有独立 `.git`，不是直接位于 GWRC checkout 中的普通子目录。
- **Skill 存在但命令找不到**：检查 `gwrc skills list` 和 PATH 中的启动器，不要仅重新复制 Markdown。
- **venv 未激活**：用户级启动器应调用安装时的解释器；若该环境被移动或删除，先卸载旧启动器，再创建新环境并重装。
- **宿主不自动调用**：使用对应宿主的显式形式，检查是否被 `disableModelInvocation` 或其他宿主配置限制。
- **数值通过但 Agent 过度解释**：这不是合格的科学验收；需要纠正结论，而不是只接受退出码 0。
