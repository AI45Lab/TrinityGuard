#!/usr/bin/env python3
"""Cross-platform installer for TrinityGuard self-guard skill."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install trinityguard-self-guard skill")
    parser.add_argument("--target", choices=["codex", "claude", "both"], default="both")
    parser.add_argument("--mode", choices=["copy", "link"], default="copy")
    parser.add_argument("--source-skill-dir", default="")
    parser.add_argument("--codex-base-dir", default="")
    parser.add_argument("--claude-base-dir", default="")
    parser.add_argument("--skip-verify", action="store_true")
    return parser.parse_args()


def resolve_source(source_skill_dir: str) -> Path:
    default_source = Path(__file__).resolve().parent.parent
    source = Path(source_skill_dir).expanduser().resolve() if source_skill_dir else default_source
    required = source / "trinityguard-self-guard-orchestrator" / "SKILL.md"
    if not required.exists():
        raise FileNotFoundError(f"Invalid skill source dir: {source}")
    return source


def default_base_dirs() -> Dict[str, Path]:
    home = Path.home()
    return {"codex": home / ".codex", "claude": home / ".claude"}


def remove_existing(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def install_one(client_name: str, base_dir: Path, mode: str, source: Path) -> Path:
    dest_root = base_dir / "skills"
    dest = dest_root / "trinityguard-self-guard"
    dest_root.mkdir(parents=True, exist_ok=True)
    remove_existing(dest)

    if mode == "copy":
        shutil.copytree(source, dest)
    else:
        try:
            dest.symlink_to(source, target_is_directory=True)
        except OSError as exc:
            raise RuntimeError(
                f"Failed to create link for {client_name} at {dest}. "
                "Use --mode copy or grant symlink permission."
            ) from exc

    print(f"[{client_name}] installed: {dest}")
    return dest


def build_targets(args: argparse.Namespace) -> List[Dict[str, Path]]:
    defaults = default_base_dirs()
    codex_base = Path(args.codex_base_dir).expanduser().resolve() if args.codex_base_dir else defaults["codex"]
    claude_base = Path(args.claude_base_dir).expanduser().resolve() if args.claude_base_dir else defaults["claude"]

    if args.target == "both":
        return [{"name": "codex", "base": codex_base}, {"name": "claude", "base": claude_base}]
    if args.target == "codex":
        return [{"name": "codex", "base": codex_base}]
    return [{"name": "claude", "base": claude_base}]


def run_verify(target_name: str, skill_dir: Path) -> None:
    verify_script = Path(__file__).resolve().parent / "verify_install.py"
    cmd = [sys.executable, str(verify_script), "--target", target_name, "--skill-dir", str(skill_dir)]
    print(f"[{target_name}] running verify_install.py ...")
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    source = resolve_source(args.source_skill_dir)
    targets = build_targets(args)

    installed: List[Dict[str, Path]] = []
    for target in targets:
        dest = install_one(target["name"], target["base"], args.mode, source)
        installed.append({"name": target["name"], "dest": dest})

    if not args.skip_verify:
        for item in installed:
            run_verify(item["name"], item["dest"])

    print("Install complete. Restart target client(s) to load new skills.")


if __name__ == "__main__":
    main()
