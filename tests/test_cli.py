"""End-to-end tests of the actual Python module command entry point."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments: object, environment: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-m", "gwrc", *(str(item) for item in arguments)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_help_and_no_command() -> None:
    help_result = run_cli("--help")
    empty_result = run_cli()

    assert help_result.returncode == 0
    assert "check-cov" in help_result.stdout
    assert "fisher-demo" in help_result.stdout
    assert empty_result.returncode == 0
    assert "usage: gwrc" in empty_result.stdout


def test_doctor_distinguishes_optional_arc() -> None:
    environment = os.environ.copy()
    environment.pop("GWRC_ARC_PAPER", None)
    result = run_cli("doctor", "--json", environment=environment)

    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    arc = next(
        check for check in document["checks"] if check["name"] == "ARC arc-paper"
    )
    assert arc["optional"]
    assert arc["state"] in {"not_configured", "available", "failed"}
    assert not arc["network_verified"]


def test_covariance_cli_and_record(tmp_path: Path) -> None:
    source = tmp_path / "cov.json"
    source.write_text(
        json.dumps({"matrix": [[2.0, 0.0], [0.0, 1.0]]}), encoding="utf-8"
    )
    output = tmp_path / "cov-run"

    result = run_cli("check-cov", source, "--output-dir", output)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["valid"]
    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert record["result"]["numerically_full_rank"]
    assert record["input_files"][0]["bytes"] == source.stat().st_size
    assert record["command"][:3] == [sys.executable, "-m", "gwrc"]
    assert (output / "report.md").is_file()


def test_invalid_covariance_has_exit_one_but_completed_record(tmp_path: Path) -> None:
    source = tmp_path / "invalid-cov.json"
    source.write_text(
        json.dumps({"matrix": [[1.0, 0.0], [0.0, -1.0]]}),
        encoding="utf-8",
    )
    output = tmp_path / "invalid-cov-run"

    result = run_cli("check-cov", source, "--output-dir", output)

    assert result.returncode == 1
    assert not json.loads(result.stdout)["valid"]
    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert record["status"] == "completed"
    assert record["errors"][0]["code"] == "negative_eigenvalue"


def test_psd_cli(tmp_path: Path) -> None:
    output = tmp_path / "psd-run"

    result = run_cli("check-psd", ROOT / "examples/psd.json", "--output-dir", output)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["valid"]
    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert record["parameters"]["convention_conversion"] == "none"


def test_psd_missing_declarations_is_a_failed_check(tmp_path: Path) -> None:
    source = tmp_path / "psd-invalid.json"
    source.write_text(
        json.dumps({"frequency": [0, 1], "psd": [1, 2]}), encoding="utf-8"
    )

    result = run_cli("check-psd", source, "--output-dir", tmp_path / "psd-invalid-run")

    assert result.returncode == 1
    errors = json.loads(result.stdout)["errors"]
    assert "missing_declarations" in {item["code"] for item in errors}


def test_fisher_demo_cli(tmp_path: Path) -> None:
    output = tmp_path / "fisher-run"

    result = run_cli("fisher-demo", "--output-dir", output)

    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert document["matches_analytic"]
    assert document["data_origin"] == "synthetic"
    assert document["calculation"]["fisher_matrix"] == [[1.25, 1.0], [1.0, 2.0]]
    assert "not LISA" in (output / "report.md").read_text(encoding="utf-8")


def test_malformed_json_is_an_input_error(tmp_path: Path) -> None:
    source = tmp_path / "broken.json"
    source.write_text('{"matrix": [', encoding="utf-8")
    output = tmp_path / "not-created"

    result = run_cli("check-cov", source, "--output-dir", output)

    assert result.returncode == 2
    assert "valid JSON" in result.stderr
    assert not result.stdout
    assert not output.exists()


def test_output_collision_does_not_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "fisher-run"
    first = run_cli("fisher-demo", "--output-dir", output)
    before = (output / "run.json").read_bytes()
    second = run_cli("fisher-demo", "--output-dir", output)

    assert first.returncode == 0
    assert second.returncode == 2
    assert "already exists" in second.stderr
    assert (output / "run.json").read_bytes() == before


def test_arc_failure_has_an_honest_failed_record(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["GWRC_ARC_PAPER"] = str(tmp_path / "not-installed")
    output = tmp_path / "arc-failed"

    result = run_cli(
        "arc-metadata",
        "arXiv:0911.3380",
        "--output-dir",
        output,
        environment=environment,
    )

    assert result.returncode == 1
    assert "GWRC_ARC_PAPER" in result.stderr
    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed"
    assert record["result"] is None
    assert record["failure"]["type"] == "IntegrationError"


def test_non_scientific_commands_avoid_heavy_imports(tmp_path: Path) -> None:
    script = (
        "from gwrc.cli.main import build_parser, main\n"
        "import sys\n"
        "build_parser()\n"
        "main(['doctor', '--json'])\n"
        f"main(['skills', 'list', '--scope', 'user', '--root', r'{tmp_path}'])\n"
        "assert 'numpy' not in sys.modules, 'non-scientific CLI imported NumPy'\n"
        "assert 'scipy' not in sys.modules, 'non-scientific CLI imported SciPy'\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
