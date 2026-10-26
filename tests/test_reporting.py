"""Reproducibility and failure-record tests."""

import hashlib
import json
from pathlib import Path

import pytest

from gwrc.core.errors import InputError, ModelError
from gwrc.core.json_utils import json_text
from gwrc.reporting.run import RunRecorder


def test_run_record_contains_digest_environment_and_scope(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    content = b'{"matrix": [[1.0]]}\n'
    source.write_bytes(content)
    output = tmp_path / "record"
    recorder = RunRecorder(
        "check-cov",
        output,
        {"matrix": [[1.0]]},
        {"convention": "test-only"},
        [source],
        ["gwrc", "check-cov", str(source)],
    )

    record = recorder.complete(
        {
            "valid": True,
            "warnings": [{"code": "same", "message": "once"}],
            "nested": {"warnings": [{"code": "same", "message": "once"}]},
        }
    )

    assert record["schema_version"] == "gwrc.run.v1"
    assert record["status"] == "completed"
    assert record["input_files"][0]["sha256"] == hashlib.sha256(content).hexdigest()
    assert record["environment"]["packages"]["numpy"]
    assert record["environment"]["packages"]["scipy"]
    assert len(record["warnings"]) == 1
    assert record["git_commit"] is None or len(record["git_commit"]) == 40
    saved = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert saved == record
    markdown = (output / "report.md").read_text(encoding="utf-8")
    assert "does not establish physical assumptions" in markdown
    assert "SHA-256" in markdown


def test_execution_failure_is_recorded_without_a_result(tmp_path: Path) -> None:
    recorder = RunRecorder("fisher-demo", tmp_path / "failed", None, {}, [])

    record = recorder.fail(ModelError("singular covariance"))

    assert record["status"] == "failed"
    assert record["result"] is None
    assert record["failure"] == {
        "type": "ModelError",
        "message": "singular covariance",
    }
    assert "singular covariance" in (tmp_path / "failed" / "report.md").read_text()


def test_existing_run_directory_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "run.json"
    sentinel.write_text("keep me", encoding="utf-8")

    with pytest.raises(InputError, match="already exists"):
        RunRecorder("check-cov", output, {}, {}, [])

    assert sentinel.read_text(encoding="utf-8") == "keep me"


def test_json_serialization_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        json_text({"condition_number": float("inf")})
