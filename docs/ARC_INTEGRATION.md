# ARC 调研与集成状态

调研和本机验证日期：2026-10-26。本文严格区分**上游文档/源码已核实**、**本机已执行验证**、**待验证**和**暂不支持**。GWRC 是独立项目，不是 ARC 官方发行版或 Fork。

## 1. 状态摘要

| 能力 | 当前状态 | 证据与边界 |
| --- | --- | --- |
| ARC v2 架构、MIT 许可、公开 CLI/Python API | 已通过官方文档和源码核实 | 见下方固定 commit 与链接 |
| GWRC 核心工具在没有 ARC 时运行 | 已实现并离线测试 | ARC 不在 `pyproject.toml` 核心依赖中 |
| 独立 `arc-paper` 环境安装 | 本机已验证 | `arc-paper 2.1.0`；AC 包 `2.2.0`；`pip check` 无冲突 |
| `arc-paper --help` 与 GWRC `doctor` 探测 | 本机已验证 | 仅证明本地 CLI 可执行，不证明论文服务可用 |
| `gwrc arc-metadata` 真实公开论文请求 | WSL2 Ubuntu 已通过；Windows 原生未接通 | Linux `completed`；Windows 上游 `ac-jobs` 锁释放报 `PermissionError`，详见第 4 节 |
| Kimi 项目 Skills 加载与 Skill 工具调用 | 本机已观察到 | 项目 Skill 被宿主发现并展开；不等于 ARC 原生插件或自动路由保证 |
| ARC 官方 runtime 安装 | Windows 未执行 setup；WSL2 Ubuntu 已通过 | Windows 的 POSIX flock 所有权不可验证；Linux 官方 runtime ready |
| Linux/macOS 官方 runtime | Linux 已验证；macOS 待验证 | WSL2 原生 checkout 和 `/tmp` 中完成真实文献流程 |
| `arc-domain`、模型摘要、managed calculate/check | 暂不支持 | 未接入，未调用模型，不伪造集成状态 |
| ALC、AC proposer-reviewer、AC jobs 作为 GWRC 记录后端 | 暂不支持 | 本阶段无适配器；ARC 自身会传递使用其所需 AC 包 |

## 2. 调研对象与版本

### 文档与源码基线

- ARC `main`：[`2b24c3277cc3b0b800cd79c77d1e64239015c64e`](https://github.com/tririver/arc/commit/2b24c3277cc3b0b800cd79c77d1e64239015c64e)，`VERSION=2.1.0`。
- AC Foundation `main`：[`a2b64f86c70a10cce0161b17bf1cf271ab0323d9`](https://github.com/tririver/ac-foundation/commit/a2b64f86c70a10cce0161b17bf1cf271ab0323d9)。
- ALC `main`：[`2251461f03326370a91b92456f02ea0108ea3890`](https://github.com/tririver/alc/commit/2251461f03326370a91b92456f02ea0108ea3890)。
- 三个上游仓库均查阅了 MIT `LICENSE`，版权归其作者。GWRC 未复制上游实现或许可证署名。

ARC 上述 `main` 的 [`runtime-sources.json`](https://github.com/tririver/arc/blob/2b24c3277cc3b0b800cd79c77d1e64239015c64e/plugins/arc/skills/arc/scripts/runtime-sources.json) 指定：

- product `b717cca9e1aec4436726b98c61e0ee27edcc0319`；
- Foundation `251c0f06bb45a4905d0b3f5e7649a40786fc2698`。

本机独立 CLI 环境使用的正是这两个提交。需要区分：检出的 `b717cca` launcher 自身又指定 product `75ce9762cd121f43e93ca1bd8199afc4643b5f90` 和同一 Foundation commit；只读官方 doctor 显示的是后者。**没有把 `75ce976` 的代码与 `b717cca` 的安装混为同一运行时。**

## 3. 上游能力的实际职责

### `arc-paper`

源码和包 README 证实其提供 arXiv、INSPIRE、DOI 元数据，缓存、结构读取、引用与被引、全文/公式检索和摘要工作流。公开接口包括：

```bash
arc-paper --help
arc-paper get-metadata arXiv:0911.3380
```

```python
from arc_paper import ArcPaperService
metadata = ArcPaperService().get_metadata("arXiv:0911.3380")
```

`get-metadata` 的 CLI 成功信封不是泛泛的 `success`：`ac.command_result.v2` 中 `status=completed`、`data` 为对象、`error=null`。这些结论来自锁定提交中的 `arc_paper/cli.py` 和 `ac_jobs/protocol.py`，GWRC adapter 据此检查响应。

### `arc-domain`

它由种子论文和研究意图构建可复用领域包，包含有证据的论文包、摘要、图谱和导出。`build` 依赖 `arc-paper`、`ac-llm` 与持久化状态，不是一个无需网络的本地关键词搜索器。MVP 不把它包装成简化搜索，也不在缺少模型时返回虚拟领域结果。

### 计算与核验工作流

`check.md` 负责笔记解析与预检，`plan.md` 负责前提和步骤，`calculate.md` 使用两个独立 calculator 和 referee，并将可信结果与备注写入版本化 work note。重试有上限，拒绝把一个 calculator 的意见自动提升为可信结论。SymPy、显式代数和数值极限是辅助证据，不是自动证明。

GWRC 借鉴显式前提、独立核验和来源记录，但本阶段使用单一 Agent 的确定性工具及显式 `gw-review`，不发起这两个 calculator 和 referee 的模型调用。

### AC Foundation 与 ALC

AC Foundation 的 `ac-jobs`、`ac-llm`、`ac-document`、`ac-proposer-reviewer` 分别负责持久化作业、模型执行、文档与提议—评议基础设施。当前直接复用的是 ARC 所需的 AC 包，而不是把这些框架重写为 GWRC 模块。GWRC 自身的小型 JSON/Markdown 记录没有改用 `ac-jobs`，避免引入不必要的编排依赖。

ALC 负责 OCR 校对、翻译、Companion 和 HTML 阅读器，不是当前文献 MVP 的依赖，也未接入。

## 4. 本机验证记录与 Windows 阻塞

### 已完成的验证

1. 在 Git 忽略的 `.local/upstream/` 检出固定源码，没有混入 GWRC Git 历史。
2. 在独立 `.local/arc-venv/` 安装上述固定源码及公开 Python 依赖，核心 `.venv` 未被 ARC 依赖污染。
3. 实际版本：`arc-paper=2.1.0`、`ac-jobs=2.2.0`、`ac-llm=2.2.0`、`ac-document=2.2.0`；`pip check` 报告无 broken requirements。
4. `arc-paper --help` 成功，列出真实 `get-metadata` 等命令。
5. 设置 `GWRC_ARC_PAPER` 后，`gwrc doctor --json` 返回 `healthy=true` 且 ARC 为 `available`，同时明确 `network_verified=false`。

### 官方 runtime 检查

只读执行官方 `arc-runtime doctor` 返回退出码 1 和 `ready=false`：`lock.probe.state=ownership_unverifiable`、`reason=ModuleNotFoundError`，锁机制为 POSIX flock。官方 runtime 文档也说明其安装锁支持 Linux/macOS。未在不适用的当前 Windows 环境中强行 setup，未删除锁文件或修改全局 AC 配置。

### WSL2 Ubuntu 完整文献流程（已通过）

随后在 WSL2 Ubuntu 中使用 `uv 0.13.5`（SHA-256 `f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f`）和 `AC_INSTALL_SOURCE=local` 运行官方 runtime。ARC 与 Foundation checkout 均为上述固定 commit，源码、runtime、venv 和缓存位于 WSL 原生 `/tmp`，不是 Windows 默认锁环境的复用，也不是默认 Git source-pin 的宣称。

Windows 挂载源码只用于创建原生 checkout，解决了 Git safe.directory 和 CRLF 对 Bash launcher 的影响；没有修改上游文件或全局 Git 配置。WSL 的 systemd 用户会话警告未阻止该流程。结果在同一运行中复制到 `.local/verification/`，避免 `/tmp` 后续清理造成证据丢失。

对 `arXiv:0911.3380` 实际完成并通过结构化检查：

- 官方 runtime `ready=true`；
- 元数据标题为 *Quasi-Single Field Inflation and Non-Gaussianities*；
- 目录返回 23 个 entries；
- `isocurvaton` 全文检索返回 25 个 occurrences；
- 成功读取 `8 Conclusion and discussion`，并保留 `data.source.document` 引用；
- `GWRC_ARC_RUNTIME` 的只读 doctor 和 `gwrc arc-metadata` 均完成，运行记录为 `status=completed`，上游响应也是 `completed`。

证据位于 Git 忽略的 `.local/verification/arc-linux-gwrc-arc-validation.IqjjpZ/results/`。`scripts/validate_arc_linux.sh` 固化相同流程。修正 workflow 的 runner 上下文后，[ARC Linux smoke 40441495383](https://github.com/ruoyuguan/gw-research-copilot/actions/runs/40441495383) 已在 GitHub Ubuntu runner 成功完成，并上传 `arc-linux-validation` artifact；论文结构检查结果与本地一致。

### 真实元数据调用失败

实际执行：

```bash
GWRC_ARC_PAPER=.local/arc-venv/Scripts/arc-paper.exe \
  .venv/Scripts/gwrc arc-metadata arXiv:0911.3380 \
  --output-dir .local/verification/arc-metadata --timeout 90
```

返回 `ac.command_result.v2`、`status=failed`、`error.code=local_io_error`、`[Errno 13] Permission denied`。GWRC 保留 `status=failed`、`result=null` 的记录，没有将其改写成成功。

公开 Python API 的堆栈定位到 `ac_jobs/lease.py` 的 Windows `msvcrt.locking(..., LK_UNLCK, 1)`。另一个不访问网络的最小 `FileLease` 实验也出现“acquire 成功、release 权限错误”，说明问题不是论文 ID 或文献内容导致。

锁定版 `lease.py` 在 Windows 分支中先 `seek(0)`、写入锁文件，再执行加锁；写入会改变当前位置，而释放时重新 `seek(0)` 解锁。[Python 官方 `msvcrt.locking` 文档](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking) 明确锁/解锁区域从当前文件位置开始，且解锁必须是此前锁定的区域。上游 `main` 与该锁定版的此文件没有差异，因此没有发现可直接采用的官方修复。

**处理决定**：本 MVP 不携带未经上游审查的 monkeypatch、锁绕过或修改版后端，也不声称 Windows 文献检索已经接通。优先建议向上游提交带 Windows 回归测试的问题/修复，再固定到已验证 commit；同时在 Linux/macOS 做独立 smoke。

## 5. GWRC 适配层与用户操作

生产适配器只通过公开 CLI 调用：

- `GWRC_ARC_PAPER` 指向独立 `arc-paper` 可执行文件，或从 `PATH` 发现；
- `GWRC_ARC_RUNTIME` 指向官方 launcher，并以 `arc-runtime arc-paper ...` 调用；两个显式变量同时设置会报配置错误；
- `doctor` 区分 `not_configured`、`available`、`failed`，且不发起文献网络请求；runtime 模式只读 `arc-runtime doctor` 并检查 `ready`，不触发懒安装；
- 子进程有超时，保留退出码和有界错误信息；
- 元数据操作严格检查 `ac.command_result.v2`、`completed`、`data` 和 `error`；
- 元数据可能来自缓存，不能将一次调用笼统声明为实际联网；
- 没有生产用模拟 ARC 后端，没有模型选择、API key 或付费调用配置。

ARC 未配置或不可用时，`gw-literature` 只能处理用户提供的资料或使用宿主实际可用的公开来源工具，并明确检索缺口。`arc-metadata` 不是全文阅读；摘要和全文主张必须有相应证据，不能由元数据扩展而来。

## 6. Kimi 与其他宿主

Kimi 官方文档确认项目级 `.agents/skills/`、目录形式 `SKILL.md`、`/skill:<name>` 和 `disableModelInvocation`：

- [Agent Skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html)
- [Plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)

本次开发中，当前宿主已实际发现 GWRC 项目 Skills 并展开直接 Skill 工具调用。该结果证明项目 Skill 路径可用，不证明所有自动选择行为，也不等于 ARC 原生 Kimi 插件。

ARC README 的官方插件安装路径覆盖 Codex、Claude Code 和 DeepSeek Harness；其 `plugins/arc/plugin.json` 不是已验证的 `kimi.plugin.json`。因此当前只声称“标准 Skills + Python CLI 桥接”，不声称 ARC 已原生安装到 Kimi。GWRC 对 Codex/Claude 的 Skill 发现和调用也未做本机 smoke，不能仅凭 Markdown 相似性声称支持。

## 7. 后续最小接入顺序

1. 以已通过的 WSL2 流程为基线，推进上游 Windows 文件锁修复和 macOS 验证；上游 Issue/PR 需另行确认。
2. 固定已验证的 ARC/AC commit，扩展少量结构读取与缓存 provenance 适配，保持默认离线。
3. 在有真实文献任务后，再评估 `arc-domain` 和 managed workflow 的模型、成本、宿主独立上下文及状态适配。
4. 只有完成目标宿主实际安装与调用测试后，才增加或声明宿主专用插件。
