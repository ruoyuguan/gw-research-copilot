"""Contracts for bilingual documentation and AI-assisted development records."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bilingual_readmes_preserve_main_document_and_cover_workflows() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    with (ROOT / "pyproject.toml").open("rb") as stream:
        metadata = tomllib.load(stream)

    assert metadata["project"]["readme"] == "README.md"
    assert "[中文](README.zh-CN.md)" in english
    assert "[English](README.md)" in chinese
    for document in (english, chinese):
        for command in (
            "python -m venv .venv",
            "gwrc skills install --scope user",
            "gwrc check-cov",
            "gwrc check-psd",
            "gwrc fisher-demo",
            "python -m pytest -q",
        ):
            assert command in document
        for text in ("K3.1 Pro", "Thinking effort: Max", "CONTRIBUTORS.md"):
            assert text in document
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document):
            if "://" not in target and not target.startswith("#"):
                assert (ROOT / target.split("#", 1)[0]).exists(), target
    assert "VS Code Codex graphical interface" in english
    assert "VS Code Codex 图形界面" in chinese


def test_ai_attribution_records_roles_sources_and_boundaries() -> None:
    contributors = (ROOT / "CONTRIBUTORS.md").read_text(encoding="utf-8")

    assert "Kimi Code (VS Code extension)" in contributors
    assert "Maintainer-reported model: **K3.1 Pro**" in contributors
    assert "Thinking effort: **Max**" in contributors
    assert "model identity was not independently established" in contributors
    assert "Codex CLI `0.162.0-alpha.17.2`" in contributors
    assert "underlying model version was not established" in contributors
    assert "not a verified VS Code Codex graphical-interface workflow" in contributors
    assert "assign legal authorship or copyright ownership" in contributors

    for filename in ("README.md", "README.zh-CN.md", "CONTRIBUTING.md"):
        assert "CONTRIBUTORS.md" in (ROOT / filename).read_text(encoding="utf-8")
    for filename in ("AGENTS.md", "docs/DEVELOPMENT.md"):
        document = (ROOT / filename).read_text(encoding="utf-8")
        assert "README.zh-CN.md" in document
        assert "CONTRIBUTORS.md" in document

    template = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text(
        encoding="utf-8"
    )
    assert "AI assistance" in template
