# Synthetic GWRC acceptance project

This directory simulates a small research project used to test GWRC from Kimi Code or Codex. It contains **synthetic data only**, not LISA, TianQin, or observational data.

`analysis.py` reads the PSD and covariance declarations without applying a sidedness conversion or assuming channel independence. It does not estimate a physical PSD or covariance and does not establish a Gaussian likelihood.

Copy this directory to an independent working folder and initialize Git there so the parent GWRC checkout's project skills are not used accidentally:

```bash
mkdir -p .local/acceptance
cp -r examples/research_project .local/acceptance/research-project
cd .local/acceptance/research-project
git init -b main
```

Then start the host in this independent project and explicitly invoke `gw-statistics`:

```text
请检查这个项目的 PSD 和协方差定义。先读取 analysis.py 和 data/，运行合适的确定性工具，保存记录并解释科学局限。
```

Expected deterministic commands (use separate new output directories):

```bash
gwrc check-psd data/psd.json --output-dir runs/psd
gwrc check-cov data/covariance.json --output-dir runs/covariance
```

A successful acceptance includes correct input reading, valid numerical reports, saved JSON/Markdown records, and an explanation that these checks do not prove the statistical model or physical interpretation. `runs/` is intentionally ignored.
