"""Install packaged Agent Skills without taking ownership of user files."""

import hashlib
import json
import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from gwrc import __version__
from gwrc.core.errors import GWRCError, InputError
from gwrc.core.json_utils import json_text

SkillScope = Literal["user", "project"]
SKILL_NAMES = ("gw-literature", "gw-review", "gw-statistics", "gw-theory")
MANIFEST_NAME = "gwrc-install.json"
MANIFEST_SCHEMA = "gwrc.skill_install.v1"


@dataclass(frozen=True)
class SkillReport:
    """Observed files and actions from an installation-related operation."""

    status: str
    scope: str
    root: str
    skills_dir: str
    skills: tuple[str, ...]
    changed: tuple[str, ...]
    preserved: tuple[str, ...]
    warnings: tuple[str, ...]
    command_path: str | None
    manifest_path: str | None
    version: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize actual installation state, including incomplete outcomes."""
        return {
            "status": self.status,
            "scope": self.scope,
            "root": self.root,
            "skills_dir": self.skills_dir,
            "skills": self.skills,
            "changed": self.changed,
            "preserved": self.preserved,
            "warnings": self.warnings,
            "command_available": self.command_path is not None,
            "command_path": self.command_path,
            "manifest_path": self.manifest_path,
            "version": self.version,
        }


def skill_resource_root() -> Path:
    """Locate canonical source-tree or wheel-packaged Skill resources."""
    packaged = Path(__file__).resolve().parent / "resources" / "skills"
    if packaged.is_dir():
        return packaged
    source = Path(__file__).resolve().parents[2] / ".agents" / "skills"
    if source.is_dir():
        return source
    raise InputError("GWRC Skill resources are missing; reinstall a complete package")


def _scope_root(scope: str, root: Path | None) -> Path:
    if scope not in ("user", "project"):
        raise InputError("scope must be 'user' or 'project'")
    if root is not None:
        return root.expanduser().resolve()
    return Path.home().resolve() if scope == "user" else Path.cwd().resolve()


def _bin_root(scope: str, root: Path, bin_dir: Path | None) -> Path | None:
    if scope == "project":
        if bin_dir is not None:
            raise InputError("--bin-dir is only meaningful for user-scope installation")
        return None
    return (
        bin_dir.expanduser().resolve()
        if bin_dir is not None
        else (root / ".local" / "bin").resolve()
    )


def _launcher_names() -> tuple[str, ...]:
    return ("gwrc", "gwrc.cmd") if os.name == "nt" else ("gwrc",)


def _expected_paths(
    scope: str, root: Path, bin_dir: Path | None
) -> tuple[Path, ...]:
    paths = [
        root / ".agents" / "skills" / name / "SKILL.md" for name in SKILL_NAMES
    ]
    if scope == "user":
        assert bin_dir is not None
        paths.extend(bin_dir / name for name in _launcher_names())
    return tuple(paths)


def _record_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _record_map(
    scope: str, root: Path, bin_dir: Path | None
) -> dict[str, Path]:
    return {
        _record_path(path, root): path
        for path in _expected_paths(scope, root, bin_dir)
    }


def _read_manifest(
    root: Path, scope: str, bin_dir: Path | None
) -> tuple[dict[str, Any], dict[str, str]]:
    path = root / ".agents" / MANIFEST_NAME
    if path.is_symlink():
        raise InputError("refusing to follow a symlinked install manifest")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read a valid GWRC install manifest: {exc}") from exc
    if not isinstance(document, dict) or document.get(
        "schema_version"
    ) != MANIFEST_SCHEMA:
        raise InputError("unrecognized install manifest; refusing to modify user files")
    if document.get("scope") != scope:
        raise InputError("install manifest scope does not match the requested scope")
    expected_bin = str(bin_dir) if bin_dir is not None else None
    if document.get("bin_dir") != expected_bin:
        raise InputError(
            "install manifest bin_dir differs; supply the original --bin-dir"
        )
    raw_files = document.get("files")
    if not isinstance(raw_files, list):
        raise InputError("install manifest files must be an array")
    expected_paths = _record_map(scope, root, bin_dir)
    records: dict[str, str] = {}
    for item in raw_files:
        if not isinstance(item, dict):
            raise InputError("install manifest contains an invalid file record")
        record, digest = item.get("path"), item.get("sha256")
        if (
            record not in expected_paths
            or record in records
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise InputError(
                "install manifest contains an unsafe or invalid file record"
            )
        records[record] = digest
    if set(records) != set(expected_paths):
        raise InputError("install manifest is incomplete or contains unmanaged files")
    return document, records


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _on_path(directory: Path) -> bool:
    target = os.path.normcase(str(directory))
    for item in os.environ.get("PATH", "").split(os.pathsep):
        if item and os.path.normcase(str(Path(item).resolve())) == target:
            return True
    return False


def _launcher_files() -> dict[str, bytes]:
    interpreter = Path(sys.executable).resolve()
    shell_path = shlex.quote(interpreter.as_posix())
    files = {
        "gwrc": (
            "#!/bin/sh\n"
            f"exec {shell_path} -m gwrc \"$@\"\n"
        ).encode()
    }
    if os.name == "nt":
        cmd_path = str(interpreter).replace("%", "%%")
        files["gwrc.cmd"] = (
            "@echo off\r\n"
            f"\"{cmd_path}\" -m gwrc %*\r\n"
            "exit /b %ERRORLEVEL%\r\n"
        ).encode()
    return files


def _expected_contents(
    scope: str, root: Path, bin_dir: Path | None
) -> dict[Path, bytes]:
    source = skill_resource_root()
    contents: dict[Path, bytes] = {}
    for name in SKILL_NAMES:
        source_path = source / name / "SKILL.md"
        if not source_path.is_file():
            raise InputError(f"missing packaged Skill: {name}")
        contents[root / ".agents" / "skills" / name / "SKILL.md"] = (
            source_path.read_bytes()
        )
    if scope == "user":
        assert bin_dir is not None
        for name, content in _launcher_files().items():
            contents[bin_dir / name] = content
    return contents


def _has_symlink_component(path: Path, boundary: Path) -> bool:
    current = path
    while current != boundary and boundary in current.parents:
        if current.is_symlink():
            return True
        current = current.parent
    return False


def _write_new(path: Path, content: bytes, root: Path) -> None:
    if _has_symlink_component(path.parent, root):
        raise InputError(
            f"refusing to write through a symlinked directory: {path.parent}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
    if path.name == "gwrc":
        path.chmod(0o755)


def _report(
    status: str,
    scope: str,
    root: Path,
    *,
    changed: list[str] | None = None,
    preserved: list[str] | None = None,
    warnings: list[str] | None = None,
    version: str | None = __version__,
    manifest_path: Path | None,
) -> SkillReport:
    skills_dir = root / ".agents" / "skills"
    present = tuple(
        name
        for name in SKILL_NAMES
        if (skills_dir / name / "SKILL.md").is_file()
    )
    return SkillReport(
        status=status,
        scope=scope,
        root=str(root),
        skills_dir=str(skills_dir),
        skills=present,
        changed=tuple(changed or []),
        preserved=tuple(preserved or []),
        warnings=tuple(warnings or []),
        command_path=shutil.which("gwrc"),
        manifest_path=str(manifest_path) if manifest_path is not None else None,
        version=version,
    )


def install_skills(
    scope: SkillScope,
    *,
    root: Path | None = None,
    bin_dir: Path | None = None,
) -> SkillReport:
    """Install packaged Skills and, for user scope, a PATH-resolved CLI launcher."""
    root_path = _scope_root(scope, root)
    bin_path = _bin_root(scope, root_path, bin_dir)
    if scope == "user" and bin_path is not None and not _on_path(bin_path):
        raise InputError(
            f"launcher directory is not on PATH: {bin_path}; choose an existing "
            "PATH directory with --bin-dir or configure PATH before installation"
        )
    expected = _expected_contents(scope, root_path, bin_path)
    manifest_path = root_path / ".agents" / MANIFEST_NAME
    if manifest_path.is_file():
        document, records = _read_manifest(root_path, scope, bin_path)
        expected_records = {
            _record_path(path, root_path): _hash_bytes(content)
            for path, content in expected.items()
        }
        def unchanged(path: Path) -> bool:
            boundary = root_path if path.is_relative_to(root_path) else bin_path
            return (
                path.is_file()
                and not path.is_symlink()
                and not _has_symlink_component(path.parent, boundary)
                and _hash_file(path) == records[_record_path(path, root_path)]
            )

        identical = records == expected_records and all(
            unchanged(path) for path in expected
        )
        if not identical:
            raise InputError(
                "an existing GWRC installation differs; "
                "uninstall it before reinstalling"
            )
        return _report(
            "already_installed",
            scope,
            root_path,
            version=document.get("gwrc_version"),
            manifest_path=manifest_path,
        )

    conflicts = [
        str(path)
        for path in expected
        if path.exists() or path.is_symlink() or path.parent.is_symlink()
    ]
    if conflicts:
        raise InputError(
            "unmanaged files would be overwritten; refusing installation: "
            + ", ".join(conflicts)
        )

    created: list[Path] = []
    try:
        for path, content in expected.items():
            _write_new(path, content, root_path)
            created.append(path)
        if scope == "user" and shutil.which("gwrc") is None:
            raise GWRCError("gwrc is not discoverable on PATH after launcher creation")
        records = [
            {
                "path": _record_path(path, root_path),
                "sha256": _hash_bytes(content),
            }
            for path, content in expected.items()
        ]
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "gwrc_version": __version__,
            "scope": scope,
            "bin_dir": str(bin_path) if bin_path is not None else None,
            "files": records,
        }
        _write_new(manifest_path, json_text(manifest).encode(), root_path)
        created.append(manifest_path)
    except Exception as exc:
        for path in reversed(created):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                continue
        if isinstance(exc, GWRCError):
            raise
        raise GWRCError(f"failed to install GWRC Skills: {exc}") from exc
    return _report("installed", scope, root_path, manifest_path=manifest_path)


def list_skills(
    scope: SkillScope,
    *,
    root: Path | None = None,
    bin_dir: Path | None = None,
) -> SkillReport:
    """Inspect installed files without assuming that a manifest implies success."""
    root_path = _scope_root(scope, root)
    bin_path = _bin_root(scope, root_path, bin_dir)
    manifest_path = root_path / ".agents" / MANIFEST_NAME
    if manifest_path.is_file():
        document, records = _read_manifest(root_path, scope, bin_path)
        warnings: list[str] = []
        complete = True
        for record, path in _record_map(scope, root_path, bin_path).items():
            boundary = root_path if path.is_relative_to(root_path) else bin_path
            if (
                path.is_symlink()
                or not path.is_file()
                or (
                    boundary is not None
                    and _has_symlink_component(path.parent, boundary)
                )
                or _hash_file(path) != records[record]
            ):
                complete = False
                warnings.append(f"missing or changed installed file: {path}")
        if scope == "user" and shutil.which("gwrc") is None:
            complete = False
            warnings.append("gwrc is not discoverable on PATH")
        return _report(
            "installed" if complete else "incomplete",
            scope,
            root_path,
            warnings=warnings,
            version=document.get("gwrc_version"),
            manifest_path=manifest_path,
        )
    present = any(
        (root_path / ".agents" / "skills" / name / "SKILL.md").is_file()
        for name in SKILL_NAMES
    )
    return _report(
        "unmanaged" if present else "not_installed",
        scope,
        root_path,
        warnings=(
            ["Skill files have no GWRC manifest; uninstall is disabled"]
            if present
            else []
        ),
        manifest_path=None,
    )


def uninstall_skills(
    scope: SkillScope,
    *,
    root: Path | None = None,
    bin_dir: Path | None = None,
) -> SkillReport:
    """Remove only unmodified GWRC-owned files and preserve user changes."""
    root_path = _scope_root(scope, root)
    bin_path = _bin_root(scope, root_path, bin_dir)
    manifest_path = root_path / ".agents" / MANIFEST_NAME
    _, records = _read_manifest(root_path, scope, bin_path)
    changed: list[str] = []
    preserved: list[str] = []
    warnings: list[str] = []
    for record, path in _record_map(scope, root_path, bin_path).items():
        boundary = root_path if path.is_relative_to(root_path) else bin_path
        if not path.exists() and not path.is_symlink():
            warnings.append(f"already missing: {path}")
            continue
        if (
            path.is_symlink()
            or (boundary is not None and _has_symlink_component(path.parent, boundary))
            or not path.is_file()
            or _hash_file(path) != records[record]
        ):
            preserved.append(str(path))
            warnings.append(f"preserved modified or unsafe path: {path}")
            continue
        path.unlink()
        changed.append(str(path))
        if path.name == "SKILL.md":
            try:
                path.parent.rmdir()
            except OSError:
                warnings.append(f"kept non-empty directory: {path.parent}")

    manifest_to_keep = manifest_path if preserved else None
    if not preserved:
        manifest_path.unlink()
    else:
        warnings.append("manifest retained to document preserved files")
    status = "partially_uninstalled" if preserved else "uninstalled"
    return _report(
        status,
        scope,
        root_path,
        changed=changed,
        preserved=preserved,
        warnings=warnings,
        manifest_path=manifest_to_keep,
    )
