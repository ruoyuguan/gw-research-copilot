"""Commands for installing, inspecting, and removing packaged Agent Skills."""

import argparse
import sys
from pathlib import Path

from gwrc.core.json_utils import json_text
from gwrc.skill_install import install_skills, list_skills, uninstall_skills


def _scope_arguments(parser: argparse.ArgumentParser, *, bin_dir: bool) -> None:
    parser.add_argument("--scope", choices=("user", "project"), required=True)
    parser.add_argument("--root", type=Path, default=None)
    if bin_dir:
        parser.add_argument("--bin-dir", type=Path, default=None)


def _dispatch(args: argparse.Namespace) -> int:
    if args.skill_action == "install":
        report = install_skills(args.scope, root=args.root, bin_dir=args.bin_dir)
    elif args.skill_action == "uninstall":
        report = uninstall_skills(args.scope, root=args.root, bin_dir=args.bin_dir)
    else:
        report = list_skills(args.scope, root=args.root, bin_dir=args.bin_dir)
    if args.skill_action == "list" and not args.json:
        print(f"Skills: {report.status}")
        print(f"Root: {report.root}")
        print(f"Installed: {', '.join(report.skills) or 'none'}")
        print(f"gwrc on PATH: {report.command_path or 'not found'}")
        for warning in report.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    else:
        sys.stdout.write(json_text(report.to_dict()))
    return 0 if report.status != "partially_uninstalled" else 1


def register_skills_commands(parser: argparse.ArgumentParser) -> None:
    """Register install, uninstall, and list without changing other CLI commands."""
    actions = parser.add_subparsers(dest="skill_action", required=True)
    for action in ("install", "uninstall"):
        command = actions.add_parser(action, help=f"{action} GWRC Agent Skills")
        _scope_arguments(command, bin_dir=True)
        command.set_defaults(handler=_dispatch)
    listing = actions.add_parser("list", help="inspect GWRC Skill installation")
    _scope_arguments(listing, bin_dir=True)
    listing.add_argument("--json", action="store_true")
    listing.set_defaults(handler=_dispatch)
