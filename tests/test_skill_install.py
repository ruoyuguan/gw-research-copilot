"""Installation tests use isolated homes and real CLI launchers."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gwrc.core.errors import InputError
from gwrc.skill_install import (
    SKILL_NAMES,
    install_skills,
    list_skills,
    skill_resource_root,
    uninstall_skills,
)


@pytest.fixture
def user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "home"
    bin_dir = root / ".local" / "bin"
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return root


def test_packaged_resources_contain_all_skills() -> None:
    root = skill_resource_root()

    assert {path.parent.name for path in root.glob("*/SKILL.md")} == set(SKILL_NAMES)
    for name in SKILL_NAMES:
        assert (root / name / "SKILL.md").read_bytes() == (
            Path(__file__).parents[1] / ".agents" / "skills" / name / "SKILL.md"
        ).read_bytes()


def test_user_install_is_idempotent_and_uninstall_preserves_extras(
    user_home: Path,
) -> None:
    other = user_home / ".agents" / "skills" / "other" / "SKILL.md"
    other.parent.mkdir(parents=True)
    other.write_text("unrelated user skill", encoding="utf-8")

    installed = install_skills("user", root=user_home)
    repeated = install_skills("user", root=user_home)

    assert installed.status == "installed"
    assert repeated.status == "already_installed"
    assert set(installed.skills) == set(SKILL_NAMES)
    assert list_skills("user", root=user_home).status == "installed"
    extra = user_home / ".agents" / "skills" / "gw-statistics" / "notes.txt"
    extra.write_text("keep my notes", encoding="utf-8")

    removed = uninstall_skills("user", root=user_home)

    assert removed.status == "uninstalled"
    assert other.read_text(encoding="utf-8") == "unrelated user skill"
    assert extra.read_text(encoding="utf-8") == "keep my notes"
    assert not (user_home / ".agents" / "gwrc-install.json").exists()
    assert list_skills("user", root=user_home).status == "not_installed"


def test_modified_files_and_manifest_are_preserved(user_home: Path) -> None:
    install_skills("user", root=user_home)
    modified = user_home / ".agents" / "skills" / "gw-statistics" / "SKILL.md"
    modified.write_text("user-edited skill", encoding="utf-8")

    removed = uninstall_skills("user", root=user_home)

    assert removed.status == "partially_uninstalled"
    assert str(modified) in removed.preserved
    assert modified.read_text(encoding="utf-8") == "user-edited skill"
    assert (user_home / ".agents" / "gwrc-install.json").is_file()
    assert not (user_home / ".agents" / "skills" / "gw-theory" / "SKILL.md").exists()
    assert list_skills("user", root=user_home).status == "incomplete"


def test_unmanaged_skill_is_never_overwritten(user_home: Path) -> None:
    existing = user_home / ".agents" / "skills" / "gw-statistics" / "SKILL.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("not a GWRC file", encoding="utf-8")

    with pytest.raises(InputError, match="unmanaged files"):
        install_skills("user", root=user_home)

    assert existing.read_text(encoding="utf-8") == "not a GWRC file"
    assert not (user_home / ".agents" / "gwrc-install.json").exists()


def test_invalid_manifest_blocks_uninstall(user_home: Path) -> None:
    install_skills("user", root=user_home)
    manifest = user_home / ".agents" / "gwrc-install.json"
    manifest.write_text("not-json", encoding="utf-8")
    before = (user_home / ".agents" / "skills" / "gw-theory" / "SKILL.md").read_bytes()

    with pytest.raises(InputError, match="valid GWRC install manifest"):
        uninstall_skills("user", root=user_home)

    installed_skill = user_home / ".agents" / "skills" / "gw-theory" / "SKILL.md"
    assert installed_skill.read_bytes() == before


def test_missing_path_fails_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    monkeypatch.setenv("PATH", str(tmp_path / "not-on-path"))

    with pytest.raises(InputError, match="not on PATH"):
        install_skills("user", root=root)

    assert not (root / ".agents").exists()


def test_project_install_does_not_create_user_launcher(tmp_path: Path) -> None:
    root = tmp_path / "research-project"

    installed = install_skills("project", root=root)

    assert installed.status == "installed"
    assert not (root / ".local" / "bin").exists()
    assert uninstall_skills("project", root=root).status == "uninstalled"


def test_launcher_runs_gwrc_outside_source_checkout(
    user_home: Path, tmp_path: Path
) -> None:
    install_skills("user", root=user_home)
    command = shutil.which("gwrc")
    assert command is not None

    completed = subprocess.run(
        [command, "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "check-cov" in completed.stdout
    if os.name == "nt":
        assert (user_home / ".local" / "bin" / "gwrc.cmd").is_file()


def test_launcher_works_in_bash(user_home: Path, tmp_path: Path) -> None:
    install_skills("user", root=user_home)
    if shutil.which("bash") is None:
        pytest.skip("Bash is unavailable")

    completed = subprocess.run(
        ["bash", "-c", "command -v gwrc && gwrc --help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "check-cov" in completed.stdout


@pytest.mark.skipif(os.name != "nt", reason="WSL fallback is Windows-specific")
def test_launcher_has_wsl_path_fallback(user_home: Path) -> None:
    install_skills("user", root=user_home)
    script = (user_home / ".local" / "bin" / "gwrc").read_text(
        encoding="utf-8"
    )
    drive = Path(sys.executable).drive.rstrip(":").lower()

    assert f"if [ -x /mnt/{drive}/" in script
    assert str(Path(sys.executable).as_posix()) in script


@pytest.mark.skipif(os.name != "nt", reason="PowerShell launcher is Windows-specific")
def test_launcher_works_in_powershell(user_home: Path, tmp_path: Path) -> None:
    install_skills("user", root=user_home)

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "gwrc --help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "check-cov" in completed.stdout


def test_custom_bin_dir_must_be_reused_for_uninstall(
    user_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    external_bin = tmp_path / "external-bin"
    monkeypatch.setenv("PATH", str(external_bin) + os.pathsep + os.environ["PATH"])
    install_skills("user", root=user_home, bin_dir=external_bin)

    with pytest.raises(InputError, match="original --bin-dir"):
        uninstall_skills("user", root=user_home)

    removed = uninstall_skills("user", root=user_home, bin_dir=external_bin)

    assert removed.status == "uninstalled"
    assert not (external_bin / "gwrc").exists()


def test_cli_install_list_and_uninstall(user_home: Path, tmp_path: Path) -> None:
    base = [sys.executable, "-m", "gwrc", "skills"]
    installed = subprocess.run(
        [*base, "install", "--scope", "user", "--root", str(user_home)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    listed = subprocess.run(
        [*base, "list", "--scope", "user", "--root", str(user_home), "--json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    removed = subprocess.run(
        [*base, "uninstall", "--scope", "user", "--root", str(user_home)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert installed.returncode == 0, installed.stderr
    assert json.loads(installed.stdout)["status"] == "installed"
    assert json.loads(listed.stdout)["status"] == "installed"
    assert removed.returncode == 0, removed.stderr
    assert json.loads(removed.stdout)["status"] == "uninstalled"
