"""Offline tests for the official ARC runtime launcher mode."""

import json
import subprocess
from pathlib import Path

import pytest

import gwrc.integrations.arc as arc_module
from gwrc.integrations.arc import ArcPaperClient, probe_arc


def runtime_path(tmp_path: Path) -> str:
    path = tmp_path / "arc-runtime"
    path.write_text("test launcher", encoding="utf-8")
    return str(path)


def completed(command, document=None, code: int = 0):
    stdout = json.dumps(document) if document is not None else "not-json"
    return subprocess.CompletedProcess(command, code, stdout=stdout, stderr="")


def test_runtime_probe_is_read_only_and_checks_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = runtime_path(tmp_path)

    def fake_run(command, **kwargs):
        assert command == [launcher, "doctor"]
        document = {"schema_version": "ac.runtime_doctor.v1", "ready": True}
        return completed(command, document)

    monkeypatch.setattr(arc_module.subprocess, "run", fake_run)
    status = ArcPaperClient(environment={"GWRC_ARC_RUNTIME": launcher}).probe()

    assert status.state == "available"
    assert status.command == (launcher,)
    assert not status.to_dict()["network_verified"]


def test_runtime_not_ready_is_not_an_available_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = runtime_path(tmp_path)
    monkeypatch.setattr(
        arc_module.subprocess,
        "run",
        lambda command, **kwargs: completed(
            command,
            {"schema_version": "ac.runtime_doctor.v1", "ready": False},
            code=1,
        ),
    )

    status = ArcPaperClient(environment={"GWRC_ARC_RUNTIME": launcher}).probe()

    assert status.state == "failed"
    assert "not ready" in status.detail


def test_runtime_rejects_unrecognized_doctor_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = runtime_path(tmp_path)
    monkeypatch.setattr(
        arc_module.subprocess,
        "run",
        lambda command, **kwargs: completed(command, {"ready": True}),
    )

    status = ArcPaperClient(environment={"GWRC_ARC_RUNTIME": launcher}).probe()

    assert status.state == "failed"
    assert "unrecognized output contract" in status.detail


def test_runtime_metadata_uses_arc_paper_subcommand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = runtime_path(tmp_path)
    envelope = {
        "schema_version": "ac.command_result.v2",
        "status": "completed",
        "data": {"title": "Runtime transport fixture"},
        "warnings": [],
        "error": None,
    }

    def fake_run(command, **kwargs):
        assert command == [
            launcher,
            "arc-paper",
            "get-metadata",
            "arXiv:0911.3380",
        ]
        return completed(command, envelope)

    monkeypatch.setattr(arc_module.subprocess, "run", fake_run)
    result = ArcPaperClient(environment={"GWRC_ARC_RUNTIME": launcher}).get_metadata(
        "arXiv:0911.3380"
    )

    assert result["arc_response"] == envelope


def test_explicit_arc_configuration_cannot_conflict(tmp_path: Path) -> None:
    status = probe_arc(
        environment={
            "GWRC_ARC_RUNTIME": str(tmp_path / "runtime"),
            "GWRC_ARC_PAPER": str(tmp_path / "paper"),
        }
    )

    assert status.state == "failed"
    assert "GWRC_ARC_RUNTIME" in status.detail
    assert "GWRC_ARC_PAPER" in status.detail


def test_empty_explicit_command_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ArcPaperClient(command=())
