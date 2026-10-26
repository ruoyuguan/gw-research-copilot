"""Verify the shipped synthetic example as a complete user workflow."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end_synthetic_example(tmp_path: Path) -> None:
    output = tmp_path / "mvp"
    completed = subprocess.run(
        [sys.executable, "examples/run_mvp.py", "--output-dir", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["all_passed"]
    assert summary["data_origin"] == "synthetic"
    assert len(summary["runs"]) == 3
    for run in summary["runs"]:
        assert run["passed"]
        assert "\\" not in run["record"]
        assert "\\" not in run["report"]
        record = json.loads((output / run["record"]).read_text(encoding="utf-8"))
        assert record["status"] == "completed"
        assert (output / run["report"]).is_file()
    markdown = (output / "summary.md").read_text()
    assert "not observational results" in markdown
    assert "](check-cov/run.json)" in markdown
