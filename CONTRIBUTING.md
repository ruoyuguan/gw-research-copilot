# Contributing to GWRC

Thank you for helping build a small, reliable research tool. Scientific correctness, explicit limitations, reproducibility, and maintainability are more important than an apparently autonomous demo.

## Development workflow

1. Open an issue describing the research or software problem before a substantial change.
2. Create a feature branch from `main`; do not commit generated research records or local environments.
3. Keep scientific APIs, CLI code, agent workflows, and external-service adapters separated.
4. Add or update offline tests and documentation for every behavior change.
5. Run the real commands affected by the change, then open a pull request for review.

```bash
git switch -c feature/short-description
python -m ruff check src tests examples
python -m pytest -q
python -m pip check
python -m build
python examples/run_mvp.py --output-dir runs/contribution-check
```

Use a new output directory when rerunning the example. The standard suite requires no network, model account, or private data. See `docs/DEVELOPMENT.md` for isolated installation and wheel checks.

## Scientific changes

For a new or changed numerical model, document:

- data types, dimensions, units, Fourier/PSD conventions, and statistical assumptions;
- the mathematical definition and its scope;
- numerical tolerances and conditioning behavior;
- analytic, independent numerical, or otherwise justified reference results;
- what a passing result does not establish.

Do not silently regularize singular matrices, guess detector conventions, describe synthetic data as observations, or call a simplified Fisher model a complete LISA/TianQin/SGWB implementation. Preserve warnings and failed checks in the run record.

For a literature or agent workflow change, distinguish retrieved evidence, model interpretation, speculation, and unavailable capabilities. Test external-service failures without converting them into successful fake responses.

## Dependencies and ARC

Keep runtime dependencies minimal. Explain why a new dependency is needed and pin an appropriate compatible range. ARC is optional; local numerical tools must install and pass tests without it. Use verified public ARC APIs and record exact compatible commits. Do not copy upstream implementations or Git history into GWRC, and retain all applicable license and attribution notices.

## Tests and pull requests

Add regression tests for fixed defects. Unit tests must be deterministic and offline by default. Live paper-provider or model tests are separate, explicitly authorized checks and are not part of normal CI.

A pull request should include:

- the problem and chosen change;
- scientific assumptions and limitations, when relevant;
- exact validation commands and their results;
- documentation and source-attribution updates;
- confirmation that no credentials, private notes, restricted collaboration material, or large research outputs are included.

Reviewers may request independent numerical checks or stronger provenance before approving scientific changes.

## Security and private research material

Never commit API keys, tokens, passwords, `.env` files, private configurations, unpublished notes, restricted collaboration data, model caches, or identifying local logs. Use the private process in `SECURITY.md` for vulnerabilities rather than a public issue.

By contributing, you agree to follow `CODE_OF_CONDUCT.md` and to license your contribution under the repository's MIT License.
