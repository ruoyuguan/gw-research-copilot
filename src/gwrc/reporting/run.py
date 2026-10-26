"""JSON and Markdown records for deterministic scientific calculations."""

import hashlib
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import scipy

from gwrc import __version__
from gwrc.core.errors import GWRCError, InputError
from gwrc.core.json_utils import json_text, to_builtin


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and commit else None


def _software() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "packages": {
            "gw-research-copilot": __version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }


def _messages(result: Any, key: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(result, dict):
        messages = result.get(key)
        if isinstance(messages, list):
            found.extend(
                message
                for message in messages
                if isinstance(message, dict) and "code" in message
            )
        for child_key, child in result.items():
            if child_key != key:
                found.extend(_messages(child, key))
    elif isinstance(result, list):
        for child in result:
            found.extend(_messages(child, key))
    return found


def _unique_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for message in messages:
        key = (str(message["code"]), str(message.get("message", "")))
        unique.setdefault(key, message)
    return list(unique.values())


def render_markdown(record: dict[str, Any]) -> str:
    """Render a human-readable summary without changing the machine record."""
    lines = [
        f"# GWRC run: {record['tool']}",
        "",
        f"- Status: **{record['status']}**",
        f"- Started: `{record['started_at']}`",
        f"- Finished: `{record['completed_at']}`",
        f"- Working-directory Git commit: `{record['git_commit'] or 'unavailable'}`",
        "",
        "## Inputs and conventions",
        "",
        "```json",
        json_text(record["parameters"]).rstrip(),
        "```",
        "",
        "## Input files",
        "",
    ]
    if record["input_files"]:
        for item in record["input_files"]:
            lines.append(
                f"- `{item['path']}` — {item['bytes']} bytes; "
                f"SHA-256 `{item['sha256']}`"
            )
    else:
        lines.append("- No external input file (built-in or identifier-only input).")
    lines.extend(["", "## Result", ""])
    if record["status"] == "failed":
        failure = record["failure"] or {}
        lines.extend(
            [
                f"**{failure.get('type', 'Error')}**: "
                f"{failure.get('message', 'Unknown failure')}",
            ]
        )
    else:
        lines.extend(["```json", json_text(record["result"]).rstrip(), "```"])
    for key, heading in (("warnings", "Warnings"), ("errors", "Validation errors")):
        lines.extend(["", f"## {heading}", ""])
        messages = record[key]
        if messages:
            lines.extend(
                f"- `{message['code']}`: {message.get('message', '')}"
                for message in messages
            )
        else:
            lines.append("- None.")
    lines.extend(
        [
            "",
            "## Scientific scope",
            "",
            (
                "A completed calculation or passing numerical check does not "
                "establish physical assumptions, a detector model, or a research "
                "conclusion. Review the stated conventions and limitations."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _command_invocation() -> list[str]:
    argv0 = Path(sys.argv[0])
    if argv0.name == "__main__.py" and argv0.parent.name == "gwrc":
        return [sys.executable, "-m", "gwrc", *sys.argv[1:]]
    return sys.argv.copy()


@dataclass
class RunRecorder:
    """Create one non-overwriting JSON and Markdown record per scientific run."""

    tool: str
    output_dir: Path | None
    input_data: Any
    parameters: dict[str, Any]
    input_files: list[Path] = field(default_factory=list)
    command: list[str] = field(default_factory=_command_invocation)
    started_at: str = field(init=False)
    directory: Path = field(init=False)

    def __post_init__(self) -> None:
        """Reserve a new run directory and capture input file digests."""
        self.started_at = _utc_now()
        if self.output_dir is None:
            stamp = self.started_at.replace(":", "").replace("-", "")
            self.directory = Path("runs") / f"{self.tool}-{stamp}-{uuid4().hex[:8]}"
        else:
            self.directory = self.output_dir
        try:
            self.directory.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise InputError(
                "run directory already exists; choose a new directory: "
                f"{self.directory}"
            ) from exc
        except OSError as exc:
            raise InputError(
                f"cannot create run directory {self.directory}: {exc}"
            ) from exc

    def _base_record(self) -> dict[str, Any]:
        files = []
        for path in self.input_files:
            try:
                files.append(
                    {
                        "path": str(path.resolve()),
                        "bytes": path.stat().st_size,
                        "sha256": _sha256(path),
                    }
                )
            except OSError as exc:
                raise InputError(f"cannot hash input file {path}: {exc}") from exc
        return {
            "schema_version": "gwrc.run.v1",
            "tool": self.tool,
            "started_at": self.started_at,
            "completed_at": _utc_now(),
            "command": self.command,
            "input": to_builtin(self.input_data),
            "input_files": files,
            "parameters": to_builtin(self.parameters),
            "environment": _software(),
            "git_commit": _git_commit(),
            "git_commit_source": "working_directory",
        }

    def _write(self, record: dict[str, Any]) -> dict[str, Any]:
        record = to_builtin(record)
        try:
            (self.directory / "run.json").write_text(
                json_text(record), encoding="utf-8", newline="\n"
            )
            (self.directory / "report.md").write_text(
                render_markdown(record), encoding="utf-8", newline="\n"
            )
        except OSError as exc:
            raise GWRCError(
                f"cannot write run record in {self.directory}: {exc}"
            ) from exc
        return record

    def complete(self, result: dict[str, Any]) -> dict[str, Any]:
        """Record a completed calculation, including failed scientific checks."""
        result = to_builtin(result)
        record = self._base_record()
        record.update(
            {
                "status": "completed",
                "result": result,
                "warnings": _unique_messages(_messages(result, "warnings")),
                "errors": _unique_messages(_messages(result, "errors")),
                "failure": None,
            }
        )
        return self._write(record)

    def fail(self, error: Exception) -> dict[str, Any]:
        """Record an expected execution failure with no fabricated result."""
        record = self._base_record()
        record.update(
            {
                "status": "failed",
                "result": None,
                "warnings": [],
                "errors": [],
                "failure": {"type": type(error).__name__, "message": str(error)},
            }
        )
        return self._write(record)


def distribution_version(name: str) -> str | None:
    """Return an installed distribution version without importing optional packages."""
    try:
        return version(name)
    except PackageNotFoundError:
        return None
