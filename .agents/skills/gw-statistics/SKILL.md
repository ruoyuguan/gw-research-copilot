---
name: gw-statistics
description: 用于引力波科研中的 PSD、协方差、Gaussian likelihood 假设和 Fisher 信息矩阵检查；不用于一般 Python 编程。
type: prompt
whenToUse: 当用户检查引力波数据的功率谱、协方差、统计假设、Gaussian 似然或 Fisher 计算，或要求复现相关数值结果时使用。
disableModelInvocation: false
---

# GW statistics

把统计约定和确定性计算分开处理。当前工具不实现完整 LISA、TianQin、DWD 或 SGWB 推断流程。

## 执行步骤

1. **明确统计对象**
   - 确认数据是时域还是频域、实值还是复值、单通道还是多通道，以及数据向量维度。
   - 区分自谱与交叉谱、单边与双边 PSD、PSD 与协方差。保留用户给出的 Fourier 归一化和单位；不要自行补因子。
   - 说明 Gaussian、独立性、噪声平稳性及通道相关性等假设是用户前提、文献结论还是待验证假设。不要默认 LISA A/E/T 相互独立。
2. **检查本地能力**
   - 科学计算前可运行 `gwrc doctor --json`。缺少核心依赖时按项目 README 安装；缺少 ARC 不影响本地数值工具。
   - 普通编程任务不要强行调用本 Skill 或科学命令。
3. **执行适用的确定性工具**
   - 协方差 JSON：`gwrc check-cov INPUT.json --output-dir NEW_RUN_DIR`。
   - 实值自谱 JSON：`gwrc check-psd INPUT.json --output-dir NEW_RUN_DIR`。
   - 合成 Fisher 参考：`gwrc fisher-demo --output-dir NEW_RUN_DIR`。
   - 复 Hermitian 矩阵或通用 `J`、`C` 使用 `gwrc.tools` 的 Python API。JSON CLI 不定义复数字面量编码。
   - 每次使用新的输出目录，不覆盖已有科研记录。输入及运行记录可能含私人数据，不得擅自公开。
4. **解释统计与数值边界**
   - `check-cov` 通过仅表示在显式容差下满足协方差检查。奇异半正定矩阵可以合法，但不适合普通逆矩阵或本 MVP 的 Fisher 求解。
   - 分别报告负特征值容差、数值秩、条件数和病态警告。不要仅依据 Cholesky 成功就声称估计稳定。
   - `check-psd` 只检查实值 auto-spectrum 数组与声明，不验证 PSD 估计过程、单位物理正确性或探测器响应。
   - Gaussian likelihood 的均值、协方差和独立性假设必须单独论证；本 MVP 没有通用 likelihood 求值器。
   - 当前 Fisher 仅为实值 Gaussian linear mean model：固定实对称正定 `C`，`F = J^T C^-1 J`。参数相关 `C`、复数据、多通道频域 inner product 和 A/E/T 通道模型均不在实现范围。
5. **必要时独立复核**
   - 用解析结果、独立线性代数路径或受控极限检查重要结果。不要把同一公式的重复执行当成独立验证。
   - 用户要求独立评议时，可显式建议 `/skill:gw-review`；不要自动启动额外模型或多 Agent 调用。

## 输出要求

- 列出输入来源、数据是否为 synthetic、矩阵/数组维度和采用的约定。
- 给出真实命令、结果、容差、警告和失败信息；不得伪造运行结果。
- 提供 `run.json` 与 `report.md` 路径；没有记录时明确说明原因。
- 分开陈述“数值检查通过”“统计模型假设已论证”“物理结论成立”，后两者不能由前者推出。
- 对未支持的模型或缺失信息列出明确限制和下一步，而不是返回看似完整的答案。
