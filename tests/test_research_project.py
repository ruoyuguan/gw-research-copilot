"""Exercise the synthetic independent research-project fixture."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "research_project"


def test_analysis_reports_explicit_synthetic_conventions() -> None:
    completed = subprocess.run(
        [sys.executable, "analysis.py"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Data origin: synthetic" in completed.stdout
    assert "PSD convention: one-sided" in completed.stdout
    assert "Covariance shape: 2 x 2" in completed.stdout
    assert "No sidedness conversion or independence assumption" in completed.stdout


def test_research_project_scientific_checks(tmp_path: Path) -> None:
    for tool, filename in (("check-psd", "psd.json"), ("check-cov", "covariance.json")):
        output = tmp_path / tool
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "gwrc",
                tool,
                str(PROJECT / "data" / filename),
                "--output-dir",
                str(output),
            ],
            cwd=PROJECT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr
        result = json.loads(completed.stdout)
        assert result["valid"]
        record = json.loads((output / "run.json").read_text(encoding="utf-8"))
        assert record["input"]["data_origin"] == "synthetic"
        assert record["status"] == "completed"
        assert (output / "report.md").is_file()


def test_invalid_examples_are_reported_not_corrected(tmp_path: Path) -> None:
    cases = (
        ("check-psd", "invalid_psd.json", {"duplicate_frequency", "negative_psd"}),
        ("check-cov", "invalid_covariance.json", {"not_hermitian"}),
    )
    for tool, filename, expected_codes in cases:
        output = tmp_path / tool
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "gwrc",
                tool,
                str(PROJECT / "data" / filename),
                "--output-dir",
                str(output),
            ],
            cwd=PROJECT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        assert completed.returncode == 1, completed.stderr
        result = json.loads(completed.stdout)
        assert not result["valid"]
        assert expected_codes <= {item["code"] for item in result["errors"]}
        record = json.loads((output / "run.json").read_text(encoding="utf-8"))
        assert record["status"] == "completed"
        assert record["input"]["data_origin"] == "synthetic"
