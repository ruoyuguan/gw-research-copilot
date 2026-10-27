## Purpose

<!-- Describe the research or software problem and the chosen change. -->

## Validation

<!-- List the exact commands actually run and their results. Do not claim unrun tests. -->

- [ ] `python -m ruff check src tests examples`
- [ ] `python -m pytest -q`
- [ ] Affected real CLI/example workflows were exercised.
- [ ] External/network behavior, if any, was tested separately and is accurately described.

## Scientific and provenance review

<!-- Complete when applicable: definitions, dimensions, assumptions, tolerances, reference results, sources, and remaining limitations. -->

- [ ] Synthetic examples are labeled and are not presented as observations.
- [ ] Numerical success is not presented as proof of physical correctness.
- [ ] Public claims match implemented and tested behavior.
- [ ] Documentation and source/ARC attribution were updated.
- [ ] Substantial AI assistance, if any, is disclosed with the tool and reliably known model/configuration details; no account secrets are included.

## Safety

- [ ] No credentials, private configurations, unpublished notes, restricted data, or generated research records are included.
- [ ] No unrelated global Agent/Git configuration or remote repository state was changed.
