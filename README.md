# GW Research Copilot (GWRC)

**Early-development research software (0.1.0).** GWRC is a host-independent set of agent workflows, deterministic scientific checks, and reproducibility records for gravitational-wave research. It is not a language model, an automated source of scientific truth, or an official product of ARC, LISA, TianQin, or any university or laboratory.

The first MVP focuses on covariance and auto-PSD validation, a deliberately limited Gaussian Fisher example, and evidence-conscious agent skills. It does **not** implement a complete LISA/TianQin analysis pipeline, a Bayesian sampler, a DWD population model, or a full SGWB Fisher calculator.

## What works locally

- `check-cov`: finite square-matrix checks, real symmetry / complex Hermitian symmetry, eigenvalues, positive semidefiniteness, numerical rank, and conditioning.
- `check-psd`: one-dimensional real auto-spectrum checks, frequency order and uniqueness, non-negativity, and required unit / spectral-convention declarations.
- `fisher-demo`: a synthetic real Gaussian mean model with a fixed covariance, solved by Cholesky factorization and compared with an analytic Fisher matrix.
- `doctor`: reports required and optional dependencies, static project-skill discovery, and optional ARC status.
- Every scientific command can write a new `run.json` and `report.md` containing input digests, parameters, software versions, timestamps, results, warnings, and failures.

A valid singular covariance is not silently treated as invertible. A passing numerical check does not establish that a Gaussian model, PSD definition, detector response, or scientific conclusion is appropriate.

## Relationship to ARC

GWRC is an independent project inspired by [Agent Research Copilot (ARC)](https://github.com/tririver/arc), not a fork or an official ARC distribution. ARC, AC Foundation, and ALC are MIT-licensed projects by their respective authors.

The optional `arc-metadata` command is a small bridge to ARC's public `arc-paper get-metadata` CLI. ARC is **not** a dependency of the numerical tools. Domain construction, model-backed summaries, and ARC's managed calculation workflows are not integrated in this MVP. See [docs/ARC_INTEGRATION.md](docs/ARC_INTEGRATION.md) for inspected commits, verified behavior, and limitations.

## Requirements and installation

Use Python 3.11 or newer and Git. Create an isolated environment in the repository root.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Windows Git Bash:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

The commands below use `gwrc` and `python` from that environment. Activate it, or replace them with the corresponding `.venv/Scripts/gwrc` / `.venv/Scripts/python` paths on Windows or `.venv/bin/...` on macOS/Linux. The `dev` extra installs offline test and build tools. For optional symbolic work, install `.[theory,dev]` instead.

Verify the installation:

```bash
gwrc --help
gwrc doctor
python -m pytest -q
```

`doctor` does not query paper providers. An unconfigured optional ARC installation does not prevent local scientific tools from working.

## Quick start with synthetic data

All files under `examples/` and the built-in Fisher demonstration are **synthetic**, not observations or detector forecasts.

```bash
gwrc check-cov examples/covariance.json --output-dir runs/covariance-demo
gwrc check-psd examples/psd.json --output-dir runs/psd-demo
gwrc fisher-demo --output-dir runs/fisher-demo
python examples/run_mvp.py --output-dir runs/mvp-demo
```

The last command executes all three CLI workflows, checks their returned results and saved records, and writes a small run index. Each `--output-dir` must be new; GWRC refuses to overwrite an existing run. Without this option, a unique directory is created below `runs/`. Run directories are Git-ignored because they can contain local paths or research inputs.

Scientific commands print their result as JSON and print record paths to stderr. Exit codes are:

- `0`: the requested numerical check or operation passed.
- `1`: a scientific check failed or an expected execution/integration failure occurred.
- `2`: command usage or input-document error.

### Input contracts

A covariance file contains a numeric matrix:

```json
{"data_origin": "synthetic", "matrix": [[2.0, 0.3], [0.3, 1.0]]}
```

A PSD file supplies arrays and declarations; see `examples/psd.json` for the complete example. Required fields are `frequency`, `psd`, `frequency_unit`, `psd_unit`, `psd_definition`, and `spectral_convention` (`one-sided` or `two-sided`). `frequency_order` defaults to `increasing` and can be `decreasing` or `unordered`. An optional `fourier_convention` is retained for review.

GWRC does not infer a one-sided/two-sided conversion factor or Fourier normalization. Negative frequencies are permitted for a two-sided spectrum but rejected for a one-sided spectrum. See [docs/SCIENTIFIC_CONVENTIONS.md](docs/SCIENTIFIC_CONVENTIONS.md) for definitions, tolerances, and scope.

The Fisher example uses `y ~ N(J theta, C)` with real data and fixed real symmetric positive-definite `C`:

```text
J = [[1, 0], [1, 1], [0, 1]]
C = diag(4, 1, 1)
F = J^T C^-1 J = [[5/4, 1], [1, 2]]
```

It contains no parameter-dependent covariance term, complex likelihood, multi-channel inner product, or detector response model.

## Agent skills and host support

The repository provides four directory-form skills:

- `gw-literature`: source-grounded reading and explicit handling of unavailable literature services.
- `gw-theory`: conventions, units, derivation checks, approximations, and independent algebra/numerical checks.
- `gw-statistics`: PSD, covariance, Gaussian-likelihood assumptions, Fisher limitations, and reproducible CLI use.
- `gw-review`: explicit, lightweight review of a result and its evidence; no automatic multi-agent fan-out.

### Kimi Code

The `.agents/skills/<name>/SKILL.md` layout and frontmatter follow the [official Kimi Skills documentation](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html). During this MVP's development on Windows, Kimi Code discovered the project skills and expanded direct Skill-tool calls to `gw-statistics` and `gw-literature`. This verifies discovery and direct loading in that environment, not exhaustive automatic routing or every slash-command path. Open the Git repository root and start a new session so project skills are scanned. The test suite validates their static structure; it does not prove a model will always choose the desired skill.

Automatic invocation is limited by each skill's domain-specific description. An obvious GW statistics, theory, or literature task can select the relevant workflow; ordinary Python or general programming does not require GWRC.

Invoke a workflow explicitly in the Kimi chat (not in a shell):

```text
/skill:gw-statistics
/skill:gw-theory
/skill:gw-literature
/skill:gw-review
```

To disable automatic invocation for one skill, edit its frontmatter in this repository:

```yaml
disableModelInvocation: true
```

Start a new session after changing skill configuration. This blocks automatic model invocation but leaves explicit `/skill:` use available; it is **not** equivalent to disabling a plugin or unloading all GWRC code. `gw-review` is manual-only by default. To avoid loading project skills entirely, run the host outside this checkout or use a checkout without `.agents/skills`; no global Kimi configuration is modified by GWRC.

### Codex, Claude Code, and other hosts

The Python CLI is independent of the agent host. The skill files use portable Markdown/YAML conventions, but their discovery and invocation on Codex and Claude Code have not been live-tested for this release; do not interpret that as verified native integration. Host-specific packaging can be added after real smoke tests. No model account, paid API, or model provider is selected by the numerical tools.

## Optional ARC metadata bridge

Install ARC separately using its official instructions and pinned sources. Then either put `arc-paper` on `PATH` or point GWRC to its executable:

```bash
export GWRC_ARC_PAPER=/path/to/arc-paper
gwrc doctor --json
gwrc arc-metadata arXiv:0911.3380 --output-dir runs/arc-metadata-demo
```

On Windows, use the environment's `arc-paper.exe` path and your shell's normal environment-variable syntax. `doctor` checks only the local CLI help contract. A successful metadata operation can use ARC's cache or a provider and does not by itself constitute a literature review.

**Current verification status:** local ARC CLI installation and `doctor` probing succeeded on Windows, but actual metadata retrieval is blocked by a reproduced upstream `ac-jobs` Windows file-lock release error. Thus `arc-metadata` is an experimental bridge, not a functioning literature service on this machine. The numerical tools are unaffected. See [docs/ARC_INTEGRATION.md](docs/ARC_INTEGRATION.md) for exact commits, evidence, and unsupported workflows. Offline tests do not require ARC.

## Development and project layout

```text
.agents/skills/       host-facing scientific workflows
src/gwrc/core/       shared validation, errors, and strict JSON handling
src/gwrc/tools/      deterministic covariance, PSD, and Fisher APIs
src/gwrc/cli/        public command grammar
src/gwrc/integrations/ optional external-service adapters
src/gwrc/reporting/  JSON and Markdown run records
tests/               offline automated tests
examples/            synthetic inputs and end-to-end runner
docs/                architecture, scientific conventions, and maintenance
.github/             CI, Dependabot, and collaboration templates
```

Run the normal checks before submitting changes:

```bash
python -m ruff check src tests examples
python -m pytest -q
python -m pip check
python -m build
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/ROADMAP.md](docs/ROADMAP.md). Contributions follow the feature-branch + pull-request workflow described in [CONTRIBUTING.md](CONTRIBUTING.md).

## License and scientific disclaimer

GWRC is distributed under the [MIT License](LICENSE). This early release is provided without warranty. Users must independently verify scientific assumptions, source claims, numerical stability, and physical interpretation. No endorsement by a gravitational-wave collaboration or academic institution is implied.
