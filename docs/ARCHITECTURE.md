# GWRC 架构与开发决策

## 1. 当前目标

0.1.0 的交付闭环是：用户或 Agent 调用公开 CLI，确定性科学工具返回结构化结果，运行记录层保存 JSON 与 Markdown。ARC 是可选外部能力，不是核心包的安装前提。

```text
Agent Skills（科研语义、约定和证据规则）
                  |
            gwrc / python -m gwrc
                  |
      +-----------+------------+
      |                        |
tools/covariance, psd, fisher integrations/arc.py
      |                        |
      +-----------+------------+
                  |
          reporting/RunRecorder
                  |
          run.json + report.md
```

## 2. 模块职责

- `core/errors.py`：`InputError` 对应退出码 2；模型与外部执行失败对应 1。
- `core/numeric.py`：显式转换到 float64/complex128，拒绝文本和 object 数组。
- `core/results.py`：稳定的机器可读消息代码。
- `core/json_utils.py`：NumPy 值转换与严格 JSON，禁止输出 NaN/Infinity。
- `tools/covariance.py`：协方差检查和独立数值诊断，不做求逆。
- `tools/psd.py`：实值 auto-spectrum 检查，不做谱估计或约定换算。
- `tools/fisher.py`：固定协方差的实 Gaussian mean Fisher 与解析演示。
- `cli/main.py`：JSON 输入、命令参数、结果输出和记录协调；非科学命令延迟加载科学依赖。
- `cli/skills.py`、`skill_install.py`：Skill 资源定位、用户级/项目级安装、清单、启动器及安全卸载。
- `integrations/arc.py`：有超时的 ARC CLI/runtime 子进程与 v2 信封检查，无内置模型或模拟服务。
- `reporting/run.py`：输入摘要、环境、结果与失败记录；不判断科学有效性。

`.agents/skills` 是工作流内容的唯一来源，wheel 通过 `force-include` 携带同一文件。科学 API 不读取 Skill 文件；只有安装器从源码或 wheel 资源读取并安装它们。Skills 通过公开 CLI/API 使用包，避免宿主逻辑污染数值实现。

## 3. 关键决策

### D1：核心独立，ARC 可选

ARC v2 的文献与模型工作流拥有独立公开 CLI。MVP 只对 `arc-paper get-metadata` 建小适配器，避免将完整运行时、模型账户和 POSIX 安装约束传递给数值用户。后续复用上游公共接口，不复制其实现。

### D2：检查与模型计算分离

`check_covariance` 可接受合法的奇异半正定矩阵并发出警告；`fisher_gaussian_mean` 则要求严格正特征值、数值满秩和可控条件数。一个 `valid` 标志不代替具体使用条件。

### D3：显式科学约定

PSD 工具要求单位、谱定义和单双边声明，但不把“声明存在”当成“声明已证明”。当前没有通用频率转换、噪声估计、通道响应或似然抽象，避免过早建立错误的通用接口。

### D4：轻量记录而非新编排平台

每次科学命令创建新目录，记录 `gwrc.run.v1`。完整机器结果在 `run.json`，人类摘要在 `report.md`。`status=completed` 只表示计算执行结束；科学检查是否通过读取 `result.valid` 或 `result.matches_analytic`。执行异常为 `status=failed`，此时 `result=null`。

记录中的 `git_commit` 来自命令工作目录，字段 `git_commit_source=working_directory`，不能误称为已安装 wheel 的上游 commit。本地路径和原始输入可能敏感，所以 `runs/` 默认被 Git 忽略。

### D5：默认离线测试

pytest 使用合成输入和传输层替身测试 ARC 错误处理，但替身不是生产后端，也不证明 ARC 可用。真实 ARC 安装和公开元数据 smoke 单独执行、单独记录。CI 不访问私有数据或付费模型。

## 4. 命令和记录约定

- stdout：科学结果或 `doctor --json` 的 JSON；记录路径写 stderr。
- 退出码 0：请求的检查通过；1：检查失败或执行失败；2：用法/输入文档错误。
- 输出目录必须不存在；默认在 `runs/` 下生成带时间和随机后缀的新目录。
- 环境记录不含主机名、账户名或 API 配置。输入路径用于本地复现，公开前必须另行审查。

## 5. 扩展边界

未来模型应先明确数据类型、维度、统计假设、参考解和容差，再增加工具。复杂频域、多通道和参数相关协方差需要新的数学契约，不能通过参数开关悄悄扩展现有 Fisher 的含义。新宿主先验证 Skill 发现和调用，再声明支持；需要打包时才增加宿主 manifest。
