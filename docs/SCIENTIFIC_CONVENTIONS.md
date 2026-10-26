# 科学约定与检查范围

## 1. 总体原则

GWRC 检查输入是否满足明确写出的数学条件。计算执行成功、数值检查通过、Agent 判断合理和科研结论成立是不同状态。所有示例均为 synthetic，不代表 LISA、TianQin 或其他探测器的观测和预报。

核心数组使用 IEEE 双精度（float64/complex128）。容差不是普遍适用的物理常数，使用者必须根据数据尺度、估计误差和模型目的审查。

## 2. 协方差

### 输入与定义

输入是非空数值方阵 `C`。实矩阵检查 `C = C^T`，复矩阵检查 Hermitian 性 `C = C^H`。包含 NaN/Inf、非方阵、非数值或非 Hermitian 输入不通过。

对通过有限性和 Hermitian 检查的矩阵，使用 `numpy.linalg.eigvalsh` 计算实特征值并按升序报告。记特征值为 `λ_i`，谱尺度为

```text
S = max_i |λ_i|
T_psd = max(eigenvalue_atol, eigenvalue_rtol * S)
T_rank = max(rank_atol, rank_rtol * S)
```

当 `min_i λ_i >= -T_psd` 时，矩阵在所给容差下为半正定。`eigenvalue_atol` 与矩阵元素同单位，相对容差无量纲。默认 PSD 容差不会将明显负特征值解释为合法。

数值秩为 `count_i(|λ_i| > T_rank)`。`numerically_full_rank=false` 表示数值秩不足，不等于严格证明矩阵在精确算术中奇异。`strictly_positive_eigenvalues` 只表示计算出的最小特征值严格大于零，也不保证求逆稳定。

### 默认容差

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `symmetry_rtol` / `symmetry_atol` | `1e-10` / `0` | `numpy.allclose(C, C^H)` 的逐元素检查 |
| `eigenvalue_rtol` / `eigenvalue_atol` | `1e-10` / `0` | 可接受负特征值的边界 |
| `rank_rtol` / `rank_atol` | `1e-12` / `0` | 数值秩判定 |
| `condition_warning` | `1e12` | 病态警告，不改变半正定合法性 |

条件指标为 `S / min_i |λ_i|`。最小绝对特征值为零时，`condition_number=null`、`condition_number_status=infinite`；比值超出浮点表示时状态为 `overflow`。其他无法计算的情形也有独立状态，绝不把 Infinity 写成非标准 JSON。

**通过的含义**：矩阵在显式数值容差下是 Hermitian 半正定。奇异矩阵仍可通过此检查，但会有数值秩和条件警告。

**不检查的含义**：矩阵是否由给定数据正确估计、样本是否独立、噪声是否 Gaussian、协方差是否对应某个探测器或物理通道。小负特征值被容差接受也不构成其物理来源的解释。

## 3. 实值 auto-PSD

当前输入是一维等长、非空、有限且显式实值的频率 `f_i` 和自谱 `P_i`。复交叉谱不在此接口范围；即使复数组虚部为零，也要求调用者先明确转换，而不是静默丢弃虚部。

必须提供：

- `frequency_unit` 与 `psd_unit`；
- `psd_definition`，说明数组表示的谱密度定义；
- `spectral_convention=one-sided` 或 `two-sided`；
- 可选 `fourier_convention`，供复核所用变换定义。

工具检查声明是否非空，不证明声明与数据来源相符。它不做 Fourier 变换、PSD 估计、窗函数修正、平均、单边/双边转换或单位量纲推断，也不自动乘除 2、采样率或 `2π`。

默认要求频率严格递增；可显式选择严格递减或 `unordered`。无序模式只取消单调性要求，仍要求有限、唯一频率。单边谱不允许负频率；双边谱允许负频率。零频率不被普遍判为非法，其可用性取决于具体模型。

默认要求所有 `P_i >= 0`，零是允许的。若显式设置 `PSDTolerances(atol, rtol)`，阈值为 `max(atol, rtol * max_i |P_i|)`，负值在该阈值内会产生警告并进入记录。绝对容差使用 PSD 单位。

通过不证明 PSD 的估计无偏、数据平稳、频率响应或单双边声明正确。

## 4. Gaussian likelihood 与 Fisher

### 当前模型

对实数据向量 `y ∈ R^n`，当前 Fisher 模型为

```text
y ~ N(J θ, C)
J_ij = ∂μ_i(θ) / ∂θ_j
F = J^T C^(-1) J
```

其中 `θ ∈ R^p`，`J ∈ R^(n×p)`，`C ∈ R^(n×n)` 是固定的实对称正定矩阵。均值关于参数线性；基准均值的常数项不影响导数。`F` 为 `p×p`。

Gaussian likelihood 一般需要均值、协方差及其统计独立/相关结构假设。本 MVP 没有通用 likelihood 求值器，也不从一次 Fisher 演示推出实际数据的 Gaussian 性。

### 数值方法

先用协方差检查验证输入，再使用 `scipy.linalg.cho_factor` 和 `cho_solve` 解 `C X = J`，计算 `J^T X`。不显式形成 `C^(-1)`，不将伪逆或任意对角正则化作为默认修复。最后对理论对称的 `F` 取其与转置的平均，仅消除浮点非对称舍入。

Fisher 额外要求最小特征值严格为正、数值满秩，并且条件数不超过 `condition_limit=1e12`（Python API 可显式调整或设为 None；无限条件仍拒绝）。容差和协方差诊断随结果保存。

合成演示：

```text
J = [[1, 0], [1, 1], [0, 1]]
C = diag(4, 1, 1)
C^(-1) = diag(1/4, 1, 1)
F_analytic = [[5/4, 1], [1, 2]]
```

输出数值 `F`、解析 `F_analytic`、最大绝对误差和默认 `rtol=atol=1e-12` 下的比较结果。

### 明确不包含

参数相关协方差的导数项、复频域数据、多通道交叉谱、特定 GW inner product、离散 Fourier 归一化、探测器响应、LISA A/E/T 通道定义、SGWB 或 DWD 物理模型均不在这个简化计算器中。后续实现必须单独写出模型假设和参考验证，不能仅给当前函数增加一个未经定义的模式参数。
