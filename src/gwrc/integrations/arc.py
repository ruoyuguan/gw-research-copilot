"""Minimal adapter for ARC's documented arc-paper command-line interface."""

import json
import math
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from gwrc.core.errors import IntegrationError


@dataclass(frozen=True)
class ARCStatus:
    """Observed optional ARC availability, never an assumed integration state."""

    state: Literal["not_configured", "available", "failed"]
    detail: str
    command: tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the status for doctor output."""
        return {
            "state": self.state,
            "optional": True,
            "detail": self.detail,
            "command": self.command,
            "network_verified": False,
        }


def _arc_command(
    environment: Mapping[str, str],
) -> tuple[tuple[str, ...], bool] | None:
    paper = environment.get("GWRC_ARC_PAPER")
    runtime = environment.get("GWRC_ARC_RUNTIME")
    if paper and runtime:
        raise IntegrationError(
            "GWRC_ARC_PAPER and GWRC_ARC_RUNTIME must not both be set"
        )
    if runtime:
        path = Path(runtime).expanduser()
        if not path.is_file():
            raise IntegrationError(
                "GWRC_ARC_RUNTIME does not point to an arc-runtime executable: "
                f"{runtime}"
            )
        return (str(path),), True
    if paper:
        path = Path(paper).expanduser()
        if not path.is_file():
            raise IntegrationError(
                "GWRC_ARC_PAPER does not point to an arc-paper executable: "
                f"{paper}"
            )
        return (str(path),), False
    discovered = shutil.which("arc-paper")
    return ((discovered,), False) if discovered else None


class ArcPaperClient:
    """Call a separately installed ARC paper CLI with bounded subprocesses."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        runtime: bool = False,
        timeout: float = 60.0,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        """Resolve a direct paper CLI, official runtime launcher, or PATH command."""
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("ARC timeout must be finite and positive")
        self.timeout = timeout
        self.environment = os.environ if environment is None else environment
        if command is not None:
            if not command:
                raise ValueError("ARC command must not be empty")
            self.command = tuple(command)
            self.runtime = runtime
        else:
            resolved = _arc_command(self.environment)
            self.command, self.runtime = resolved or (None, runtime)

    def _run(
        self,
        arguments: Sequence[str],
        timeout: float,
        *,
        runtime_doctor: bool = False,
    ) -> str:
        if self.command is None:
            raise IntegrationError(
                "ARC is not configured. Install arc-paper separately, set "
                "GWRC_ARC_PAPER, or configure GWRC_ARC_RUNTIME; local "
                "scientific tools remain available."
            )
        operation = "arc-runtime doctor" if runtime_doctor else "arc-paper"
        command = list(self.command)
        if self.runtime and not runtime_doctor:
            command.append("arc-paper")
        command.extend(arguments)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise IntegrationError(
                f"{operation} exceeded the {timeout:g}-second timeout"
            ) from exc
        except OSError as exc:
            raise IntegrationError(f"cannot execute {operation}: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise IntegrationError(
                f"{operation} exited with code {completed.returncode}: {detail[:2000]}"
            )
        return completed.stdout

    def _probe_runtime(self) -> ARCStatus:
        try:
            output = self._run(
                ("doctor",), min(self.timeout, 15.0), runtime_doctor=True
            )
            document = json.loads(output)
        except IntegrationError as exc:
            return ARCStatus(
                "failed",
                f"ARC runtime is not ready or doctor failed: {exc}",
                self.command,
            )
        except json.JSONDecodeError:
            return ARCStatus(
                "failed", "arc-runtime doctor returned invalid JSON", self.command
            )
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != "ac.runtime_doctor.v1"
        ):
            return ARCStatus(
                "failed",
                "arc-runtime doctor returned an unrecognized output contract",
                self.command,
            )
        if document.get("ready") is not True:
            return ARCStatus(
                "failed",
                "ARC runtime is not ready; run the official setup before research",
                self.command,
            )
        return ARCStatus(
            "available",
            "ARC runtime doctor reports ready; paper-network access is not tested",
            self.command,
        )

    def probe(self) -> ARCStatus:
        """Check local CLI readiness without installing or querying providers."""
        if self.command is None:
            return ARCStatus(
                "not_configured",
                "ARC is optional and arc-paper was not found; "
                "local tools are available",
            )
        if self.runtime:
            return self._probe_runtime()
        try:
            output = self._run(("--help",), min(self.timeout, 15.0))
        except IntegrationError as exc:
            return ARCStatus("failed", str(exc), self.command)
        if "usage" not in output.lower():
            return ARCStatus(
                "failed",
                "arc-paper --help returned an unrecognized output contract",
                self.command,
            )
        return ARCStatus(
            "available",
            "arc-paper --help succeeded; paper-network access is not tested by doctor",
            self.command,
        )

    def get_metadata(self, paper_id: str) -> dict[str, Any]:
        """Retrieve real ARC metadata and validate its typed JSON envelope."""
        if not paper_id.strip():
            raise IntegrationError("paper_id must not be empty")
        output = self._run(("get-metadata", paper_id), self.timeout)
        try:
            response = json.loads(output)
        except json.JSONDecodeError as exc:
            raise IntegrationError("arc-paper returned invalid JSON") from exc
        if not isinstance(response, dict) or not isinstance(
            response.get("status"), str
        ):
            raise IntegrationError("arc-paper response lacks a typed status envelope")
        if response.get("schema_version") != "ac.command_result.v2":
            raise IntegrationError(
                "unsupported ARC command-result schema: "
                + json_text_for_error(response)
            )
        if (
            response["status"] != "completed"
            or response.get("error") is not None
            or not isinstance(response.get("data"), dict)
        ):
            raise IntegrationError(
                "ARC metadata request was not successful: "
                + json_text_for_error(response)
            )
        return {
            "paper_id": paper_id,
            "backend": "ARC arc-paper public CLI",
            "arc_response": response,
            "retrieval_completed": True,
            "scientific_validation": "metadata retrieval only; not a literature review",
        }


def json_text_for_error(response: dict[str, Any]) -> str:
    """Keep a bounded upstream error envelope for actionable diagnostics."""
    try:
        text = json.dumps(response, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(response)
    return text[:2000]


def probe_arc(
    *, environment: Mapping[str, str] | None = None
) -> ARCStatus:
    """Report missing, working, and broken optional ARC installations distinctly."""
    try:
        return ArcPaperClient(environment=environment).probe()
    except IntegrationError as exc:
        return ARCStatus("failed", str(exc))
