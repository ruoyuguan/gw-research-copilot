# GWRC 用户验收与证据分级

## 1. 验收目标

目标用户在自己的项目中完成一次自然语言科学检查：发现或显式调用 `gw-statistics`，读取正确输入，执行确定性工具，保存运行记录，并解释科学局限。

本文件区分三类证据，不能相互替代：

1. **自动化工程验证**：离线测试、wheel、安装器、Bash/PowerShell 和独立目录检查。
2. **维护者真实宿主 smoke**：在实际 Kimi/Codex VS Code 中执行下面的任务。
3. **未参与开发的组员验收**：由一名新用户按照文档独立完成。只有这一类证据满足最终 v0.2.0 用户验收目标，不能由开发者脚本或模型自我声明替代。

默认 pytest 不调用模型。真实宿主 smoke 使用测试者已有账户，可能消耗额度，应限制为一个任务并与离线 CI 分开。

## 2. 准备独立研究项目

本清单对应的验收提交为 `7e7602d5aee2efb84573b3beafeca4718fdf46d0`。不要使用尚未包含候选安装功能的旧 `main`：

```bash
git clone --branch feature/cross-project-agent \
  https://github.com/ruoyuguan/gw-research-copilot.git
cd gw-research-copilot
git checkout 7e7602d5aee2efb84573b3beafeca4718fdf46d0
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

## 6. 维护者 smoke 实测记录（2026-10-27）

以下均为维护者测试，不是未参与开发的组员验收。原始事件日志包含本机路径，只保留在 Git 忽略的 `.local/acceptance/`，不公开上传。

### Kimi：维护者工作流通过

在独立 synthetic 项目中，通过用户级安装调用 `gw-statistics`，读取了 `analysis.py` 和四个输入文件。`runs/kimi-psd`、`runs/kimi-covariance` 的记录为 `status=completed`、`valid=true`，并生成了 `run.json` 和 `report.md`。负例 `runs/kimi-invalid-psd`、`runs/kimi-invalid-covariance` 的诊断执行完成但 `valid=false`，分别包含 `duplicate_frequency`、`negative_psd` 和 `not_hermitian`；没有修改输入来强迫通过。

这些记录只证明数组、矩阵和声明检查按定义执行，不证明 PSD 估计、Gaussian likelihood、通道独立性或物理结论。

### Codex CLI：部分通过，未通过端到端验收

- 环境为 Windows，VS Code 扩展 `openai.chatgpt@26.1007.21434` 附带的 `codex-cli 0.162.0-alpha.17.2`，使用测试者已有 ChatGPT 登录。测试输入来自验收提交 `7e7602d5aee2efb84573b3beafeca4718fdf46d0`，独立目录有自己的 `.git`，用户级 GWRC 安装报告为 `0.1.0`。
- 预检中，`gwrc skills list --scope user --json` 返回 `installed` 和 `command_available=true`，`analysis.py` 正确报告 synthetic、单边 PSD、4 个频率点和 2×2 协方差。
- `codex exec` 使用 `--sandbox workspace-write`、`--ephemeral` 和独立 `--cd` 目录，没有使用绕过审批或沙箱的选项。`$gw-statistics` 确实被识别，Agent 读取了用户级 `~/.agents/skills/gw-statistics/SKILL.md`、`analysis.py` 和全部 synthetic 输入。这验证了 Codex CLI 的用户级 Skill 发现和读取，不只是检查文件是否存在。
- 但四条 `gwrc check-psd`/`check-cov` 命令都未能启动 GWRC，实际退出码均为 101，而不是科学诊断的 0 或 1。启动器报告 `Unable to create process`；进一步直接启动当前 Microsoft Store Python 时得到 `Access is denied`。普通宿主外的预检成功不能替代这个沙箱内结果。
- 测试期间出现 WebSocket 重连并回退到 HTTPS。后续命令又遇到 PowerShell 脚本执行策略拒绝和停滞，维护者约 11 分钟后停止任务。没有正常结束时的 Agent 总结，因此最终科学解释也未通过验收。
- 停止后复核五个输入文件的 SHA-256，均与测试前一致。指定的四个输出目录均没有 GWRC `run.json`；Agent 尝试的替代 PowerShell 检查不被计为 GWRC 科学工具或验收记录。

**初次结论：Codex CLI 的 Skill 发现与输入读取已通过，但在当时的 Microsoft Store Python 环境中，科学命令执行、标准记录和完整工作流未通过。此次没有操作 VS Code Codex 图形界面，也不能把本测试算作独立组员验收。**

初次失败不能通过关闭沙箱、绕过审批或放宽 PowerShell 执行策略来掩盖。先用无模型诊断确定执行环境问题，再决定是否复验；替代脚本和手工结论都不能代替 GWRC 运行记录。

### Codex CLI 修正环境后的复验：维护者端到端通过

- 使用 `codex sandbox --permission-profile :workspace` 进行无模型诊断，复现了 Microsoft Store Python 的退出码 101。随后在 Git 忽略的 `.local/` 中通过 uv 0.13.5 安装标准 CPython 3.12.15，并在新 venv 中安装 GWRC 0.1.0 wheel、NumPy 2.5.4 和 SciPy 1.18.1；依赖检查通过。uv 只是本次测试工具，不是 GWRC 新增运行依赖。
- 在 `:workspace` 沙箱中，新 Python 可加载 NumPy/SciPy，四个确定性检查分别返回预期的 0、0、1、1，负例报告相应错误，输入哈希不变。按安装器的安全卸载/重装流程更新用户级启动器后，Bash、PowerShell 和沙箱中的真实 `gwrc` 均可执行，记录确认使用新解释器。没有修改 PATH、宿主配置或执行策略，旧 `.venv` 保留用于回退。
- 修正后仅运行一次新的 Agent 任务，使用来自同一验收提交的干净独立项目，以及与前次相同的 `codex exec --sandbox workspace-write --ephemeral` 方式。任务正常结束，事件日志中的四条实际命令退出码依次为 0、0、1、1。
- 四份 `run.json` 和 `report.md` 均存在。两个正例为 `status=completed`、`valid=true`；两个负例为 `status=completed`、`valid=false`，包含 `duplicate_frequency`、`negative_psd` 和 `not_hermitian`。结构化复核确认输入 digest、新 Python 环境和命令参数正确，五个输入文件的 SHA-256 均未改变。
- 最终回答明确数据为 synthetic，给出实际命令、退出码和记录路径，并区分数值检查、统计假设和物理结论。它没有把非法输入解释成有效结果，也没有声称 Gaussian、通道独立性、PSD 估计或物理模型已获证明。

**复验结论：在上述 Windows、Codex CLI 和标准 CPython 环境中，用户级 `$gw-statistics` 的维护者端到端工作流通过。VS Code Codex 图形界面、自动路由、其他 Python 发行版及未参与开发的组员验收仍未完成；不能用此结果推断 GUI 已支持或 v0.2.0 用户验收条件已满足。**

## 7. 常见问题

- **只有源码仓库中的 Skill 被发现**：确认测试项目有独立 `.git`，不是直接位于 GWRC checkout 中的普通子目录。
- **Skill 存在但命令找不到**：检查 `gwrc skills list` 和 PATH 中的启动器，不要仅重新复制 Markdown。
- **venv 未激活**：用户级启动器应调用安装时的解释器；若该环境被移动或删除，先卸载旧启动器，再创建新环境并重装。
- **宿主不自动调用**：使用对应宿主的显式形式，检查是否被 `disableModelInvocation` 或其他宿主配置限制。
- **数值通过但 Agent 过度解释**：这不是合格的科学验收；需要纠正结论，而不是只接受退出码 0。
