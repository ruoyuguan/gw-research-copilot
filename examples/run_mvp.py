"""Run the complete synthetic GWRC MVP workflow through its real CLI."""

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from gwrc.core.json_utils import json_text

ROOT = Path(__file__).resolve().parents[1]


def _invoke(
    arguments: Sequence[str],
    record_directory: Path,
    passed: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    command = [sys.executable, "-m", "gwrc", *arguments]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"GWRC example command failed ({completed.returncode}): "
            f"{' '.join(command)}\n{completed.stderr}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GWRC example command did not return JSON") from exc
    if not passed(result):
        raise RuntimeError(f"GWRC example result did not pass: {completed.stdout}")
    record_path = record_directory / "run.json"
    report_path = record_directory / "report.md"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record["status"] != "completed" or not report_path.is_file():
        raise RuntimeError(f"Incomplete GWRC record: {record_directory}")
    return {
        "command": command,
        "passed": True,
        "record": record_path.relative_to(record_directory.parent).as_posix(),
        "report": report_path.relative_to(record_directory.parent).as_posix(),
    }


def main() -> int:
    """Execute covariance, PSD, and Fisher checks and write a verified index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new directory for the three runs and summary",
    )
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    jobs = [
        (
            "check-cov",
            [str(ROOT / "examples/covariance.json")],
            lambda result: result["valid"],
        ),
        (
            "check-psd",
            [str(ROOT / "examples/psd.json")],
            lambda result: result["valid"],
        ),
        (
            "fisher-demo",
            [],
            lambda result: result["matches_analytic"],
        ),
    ]
    runs = []
    for tool, arguments, passed in jobs:
        directory = output / tool
        runs.append(
            _invoke(
                [tool, *arguments, "--output-dir", str(directory)],
                directory,
                passed,
            )
        )
    summary = {
        "schema_version": "gwrc.synthetic_mvp_example.v1",
        "data_origin": "synthetic",
        "all_passed": True,
        "runs": runs,
        "scope": (
            "Deterministic synthetic checks only; no detector data or ARC network call."
        ),
    }
    (output / "summary.json").write_text(json_text(summary), encoding="utf-8")
    lines = [
        "# Synthetic GWRC MVP demonstration",
        "",
        "All three real CLI calls and their saved records were verified.",
        "These are synthetic numerical examples, not observational results.",
        "",
    ]
    lines.extend(
        f"- `{run['command'][3]}`: [run record]({run['record']}); "
        f"[Markdown report]({run['report']})"
        for run in runs
    )
    lines.append("")
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    sys.stdout.write(json_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
