"""Offline transport tests for the optional ARC adapter."""

import json
import subprocess
from pathlib import Path

import pytest

import gwrc.integrations.arc as arc_module
from gwrc.core.errors import IntegrationError
from gwrc.integrations.arc import ArcPaperClient, probe_arc


def completed_process(args: list[str], stdout: str, code: int = 0):
    return subprocess.CompletedProcess(args, code, stdout=stdout, stderr="")


def test_missing_arc_leaves_local_tools_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(arc_module.shutil, "which", lambda name: None)

    status = probe_arc(environment={})

    assert status.state == "not_configured"
    with pytest.raises(
        IntegrationError, match="local scientific tools remain available"
    ):
        ArcPaperClient(environment={}).get_metadata("arXiv:0911.3380")


def test_bad_explicit_arc_path_is_a_failed_check(tmp_path: Path) -> None:
    status = probe_arc(
        environment={"GWRC_ARC_PAPER": str(tmp_path / "missing-arc-paper")}
    )

    assert status.state == "failed"
    assert "GWRC_ARC_PAPER" in status.detail


def test_probe_checks_help_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, **kwargs):
        assert command == ["arc-paper", "--help"]
        return completed_process(command, "usage: arc-paper [--help]")

    monkeypatch.setattr(arc_module.subprocess, "run", fake_run)
    status = ArcPaperClient(command=("arc-paper",)).probe()

    assert status.state == "available"
    assert not status.to_dict()["network_verified"]


def test_metadata_uses_actual_arc_v2_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = {
        "schema_version": "ac.command_result.v2",
        "status": "completed",
        "data": {"title": "Transport fixture", "identifiers": {"arxiv": "0911.3380"}},
        "warnings": [],
        "error": None,
    }

    def fake_run(command, **kwargs):
        assert command == ["arc-paper", "get-metadata", "arXiv:0911.3380"]
        return completed_process(command, json.dumps(envelope))

    monkeypatch.setattr(arc_module.subprocess, "run", fake_run)
    result = ArcPaperClient(command=("arc-paper",)).get_metadata("arXiv:0911.3380")

    assert result["arc_response"] == envelope
    assert result["retrieval_completed"]
    assert "network_request_executed" not in result


def test_failed_arc_envelope_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = {
        "schema_version": "ac.command_result.v2",
        "status": "failed",
        "data": {},
        "error": {"code": "provider_unavailable", "message": "offline"},
    }
    monkeypatch.setattr(
        arc_module.subprocess,
        "run",
        lambda command, **kwargs: completed_process(command, json.dumps(envelope)),
    )

    with pytest.raises(IntegrationError, match="provider_unavailable"):
        ArcPaperClient(command=("arc-paper",)).get_metadata("arXiv:test")


def test_invalid_json_and_nonzero_exit_are_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        arc_module.subprocess,
        "run",
        lambda command, **kwargs: completed_process(command, "not-json"),
    )
    with pytest.raises(IntegrationError, match="invalid JSON"):
        ArcPaperClient(command=("arc-paper",)).get_metadata("arXiv:test")

    def failed_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 1, stdout="", stderr="provider offline"
        )

    monkeypatch.setattr(arc_module.subprocess, "run", failed_run)
    with pytest.raises(IntegrationError, match="provider offline"):
        ArcPaperClient(command=("arc-paper",)).get_metadata("arXiv:test")


def test_arc_timeout_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(arc_module.subprocess, "run", timeout)
    with pytest.raises(IntegrationError, match="timeout"):
        ArcPaperClient(command=("arc-paper",), timeout=0.1).get_metadata("arXiv:test")


def test_probe_rejects_unrecognized_help(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        arc_module.subprocess,
        "run",
        lambda command, **kwargs: completed_process(command, "unexpected output"),
    )
    status = ArcPaperClient(command=("arc-paper",)).probe()

    assert status.state == "failed"


def test_non_finite_arc_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        ArcPaperClient(command=("arc-paper",), timeout=float("nan"))
