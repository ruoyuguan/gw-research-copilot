# GWRC 开发约定

## 目标与边界

GWRC 提供宿主无关的引力波科研 Skills、确定性数值工具和可复现记录。先保证小而可靠，不把模型推理、数值成功和科研结论混为一谈。本阶段不开发 Web、多用户平台、数据库、HPC 自动化或完整探测器数据流水线。

## 工程结构

- `src/gwrc/tools/` 只放可独立测试的科学 API，不读取 Agent 配置或调用模型。
- `src/gwrc/cli/` 负责输入文档、退出码和用户交互。
- `src/gwrc/integrations/` 只封装已核实的公开外部接口；外部能力缺失不得影响核心工具。
- `src/gwrc/reporting/` 负责运行记录，不包含科学判据。
- `.agents/skills/` 描述工作流，不作为 Python 包的运行时依赖。
- 文档主要使用中文；README 与国际社区文件使用英文。公共 Python API 使用类型标注和 docstring，遵循 PEP 8。

## 科学不变量

1. 不猜测 Fourier 归一化、单双边 PSD 转换、探测器响应或 A/E/T 通道定义。
2. 区分正半定、严格正定、数值秩与病态；不得用伪逆或加对角正则化偷偷“修复”输入。
3. 当前 Fisher 仅限实值 Gaussian linear mean、固定实对称正定协方差。扩展时必须写出新模型并添加解析或独立参考测试。
4. 数值容差必须进入结果与运行记录。绝对容差的单位应与被检查量一致。
5. 示例必须标明 synthetic；真实观测、受限合作资料和未发表笔记默认不提交、不上传。
6. 数值检查通过不证明统计假设或物理结论。文档不得宣称自动科研正确性。

## 验证与协作

在项目虚拟环境中运行：

```bash
python -m ruff check src tests examples
python -m pytest -q
python -m pip check
python -m build
```

至少再执行受影响的真实 CLI 和 `python examples/run_mvp.py --output-dir <new-dir>`。默认测试不联网、不调用大模型；ARC 实际联网验证单独记录，不能用 mock 传输测试替代。

使用 feature branch + Pull Request。不要提交 `.venv*`、`.local/`、`runs/`、缓存、私有输入、`.env`、密钥或个人日志。修改公共命令、科学约定或目录职责时，同步更新 README、相关文档和测试。引用 ARC 或其他上游代码时保留其许可证和署名；GWRC 不是 ARC 官方项目。

未经用户明确授权，不修改全局 Agent/Git 配置，不创建组织，不公开仓库，不推送远程。首次公开前必须检查暂存内容、完整历史与 secret scanning，并单独取得确认。
