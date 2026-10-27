"""Static contract checks for project-level Agent Skills."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"gw-literature", "gw-theory", "gw-statistics", "gw-review"}


def skill_documents():
    for name in sorted(EXPECTED):
        path = ROOT / ".agents" / "skills" / name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        _, frontmatter, body = text.split("---", 2)
        yield name, yaml.safe_load(frontmatter), body


def test_all_skills_have_valid_directory_form_frontmatter() -> None:
    for name, metadata, body in skill_documents():
        assert metadata["name"] == name
        assert isinstance(metadata["description"], str)
        assert metadata["description"].strip()
        assert "\n" not in metadata["description"]
        assert metadata["type"] == "prompt"
        assert isinstance(metadata["whenToUse"], str) and metadata["whenToUse"]
        assert isinstance(metadata["disableModelInvocation"], bool)
        assert body.strip()


def test_skill_automation_policy_is_explicit() -> None:
    documents = {name: metadata for name, metadata, _ in skill_documents()}

    assert set(documents) == EXPECTED
    assert documents["gw-review"]["disableModelInvocation"]
    for name in EXPECTED - {"gw-review"}:
        assert not documents[name]["disableModelInvocation"]


def test_statistics_skill_references_real_commands() -> None:
    body = (ROOT / ".agents/skills/gw-statistics/SKILL.md").read_text(encoding="utf-8")

    assert "gwrc check-cov" in body
    assert "gwrc check-psd" in body
    assert "gwrc fisher-demo" in body
    assert "J^T" in body
    assert "奇异" in body


def test_installation_docs_pin_candidate_and_limit_codex_claims() -> None:
    installation = (ROOT / "docs/INSTALLATION.md").read_text(encoding="utf-8")
    acceptance = (ROOT / "docs/ACCEPTANCE.md").read_text(encoding="utf-8")

    for document in (installation, acceptance):
        assert "git clone --branch feature/cross-project-agent" in document
        assert "git checkout 7e7602d5aee2efb84573b3beafeca4718fdf46d0" in document
    assert "尚待真实宿主验证" in installation
