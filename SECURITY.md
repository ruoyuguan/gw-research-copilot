# Security Policy

## Supported version

GWRC is in early development. Security fixes are applied to the current `main` branch; no long-term support branches are provided at this stage.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability, leaked credential, or exposed private research material.

Preferred channel: use GitHub's private vulnerability reporting for this repository **if that feature is shown as enabled**. Otherwise, contact the repository owner through a private contact method listed on the owner's GitHub profile. Do not post secrets or private data in an issue, pull request, log, or public discussion.

Include the affected commit or version, impact, a minimal reproduction, and suggested mitigation when available. Remove credentials and private research content from the report itself. Maintainers will assess the report as project resources permit; no fixed response-time guarantee is made for this early community project.

## Research-data boundary

Public source code, generic skills, synthetic examples, and documentation belong in the repository. The following do not:

- credentials, `.env` files, private agent configuration, or personal tokens;
- unpublished papers, internal notes, or personally identifying logs;
- restricted LISA Consortium or other collaboration material;
- unauthorized collaborator data, large research datasets, model caches, or generated run records.

GWRC records input paths, hashes, raw JSON inputs, software versions, and results. Treat `runs/` as local research data and review it before sharing. A hash does not make sensitive content safe to publish.

If a secret is accidentally committed, revoke/rotate it first, then remove it from the complete Git history before public distribution. Deleting only the latest working-tree copy is insufficient.

## Optional integrations

ARC and other external services have their own security and credential policies. GWRC does not accept or store their API keys. Do not place credentials in command arguments, skill files, issue reports, or committed configuration. Network and model-backed capabilities are not part of the default CI test suite.
