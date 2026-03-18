#!/usr/bin/env python3
"""Cross-platform installer for TrinityGuard self-guard skill (Codex only)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


AGENTS_MARKER = "<TRINITYSAFE_GUARD_BLOCK>"
AGENTS_BLOCK = f"""# {AGENTS_MARKER}
- TrinitySafeSkills runtime hook must run before every final response.
- Do not skip this check for explanatory/summarization answers.

## TrinitySafeSkills Mandatory Runtime Check
1. Build per-turn input JSON under `./.codex/logs/`.
2. Run:
```powershell
python ./.codex/skills/trinityguard-self-guard/shared/scripts/self_guard_runtime_hook_template.py `
  ./.codex/logs/self_guard_input_<turn>.json `
  --policy ./.codex/skills/trinityguard-self-guard/shared/references/runtime_policy.template.json `
  --policy-profile balanced `
  --log-layout turn_dir `
  --turns-dir ./.codex/logs/turns `
  --index-log ./.codex/logs/index.jsonl `
  --state-dir ./.codex/logs/.self_guard_state `
  --out ./.codex/logs/runtime_hook_summary.json
```
3. Treat check as complete only when `Turn dir`, `Result path`, and `Index log path` are emitted.
4. Read `final_action` from `runtime_hook_summary.json` before final output.
5. Final response must include:
   - `self_guard_final_action`
   - `self_guard_trace_id`
   - `self_guard_events_log` (`./.codex/logs/index.jsonl`)
# </TRINITYSAFE_GUARD_BLOCK>
"""

AGENTS_FEATURE_STRINGS = [
    "TrinitySafeSkills Mandatory Runtime Check",
    "self_guard_runtime_hook_template.py",
    "--log-layout turn_dir",
    "self_guard_events_log",
]


def has_trinitysafe_block(existing: str) -> bool:
    if AGENTS_MARKER in existing:
        return True
    hit_count = sum(1 for token in AGENTS_FEATURE_STRINGS if token in existing)
    return hit_count >= 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install trinityguard-self-guard skill")
    parser.add_argument("--target", choices=["codex"], default="codex")
    parser.add_argument("--mode", choices=["copy", "link"], default="copy")
    parser.add_argument("--source-skill-dir", default="")
    parser.add_argument("--codex-base-dir", default="")
    parser.add_argument("--skip-verify", action="store_true")
    return parser.parse_args()


def resolve_source(source_skill_dir: str) -> Path:
    default_source = Path(__file__).resolve().parent.parent
    source = Path(source_skill_dir).expanduser().resolve() if source_skill_dir else default_source
    required = source / "trinityguard-self-guard-orchestrator" / "SKILL.md"
    if not required.exists():
        raise FileNotFoundError(f"Invalid skill source dir: {source}")
    return source


def resolve_codex_home(base_hint: str) -> Path:
    if not base_hint:
        return Path.home() / ".codex"

    base = Path(base_hint).expanduser().resolve()
    if base.name.lower() == ".codex":
        return base
    return base / ".codex"


def resolve_project_root_for_agents(base_hint: str) -> Optional[Path]:
    if not base_hint:
        return None
    base = Path(base_hint).expanduser().resolve()
    if base.name.lower() == ".codex":
        return base.parent
    return base


def default_base_dirs() -> Dict[str, Path]:
    return {"codex": resolve_codex_home("")}


def remove_existing(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def install_one(client_name: str, codex_home: Path, mode: str, source: Path) -> Path:
    dest_root = codex_home / "skills"
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
    codex_home = resolve_codex_home(args.codex_base_dir) if args.codex_base_dir else defaults["codex"]
    return [{"name": "codex", "base": codex_home}]


def run_verify(target_name: str, skill_dir: Path) -> None:
    verify_script = Path(__file__).resolve().parent / "verify_install.py"
    cmd = [sys.executable, str(verify_script), "--target", target_name, "--skill-dir", str(skill_dir)]
    print(f"[{target_name}] running verify_install.py ...")
    subprocess.run(cmd, check=True)


def ensure_agents_md(project_root: Optional[Path]) -> None:
    if project_root is None:
        print("[codex] skip AGENTS.md injection: no explicit --codex-base-dir provided.")
        return

    agents_path = project_root / "AGENTS.md"
    if agents_path.exists():
        existing = agents_path.read_text(encoding="utf-8-sig")
        if AGENTS_MARKER in existing:
            print(f"[codex] AGENTS.md already contains TrinitySafe block: {agents_path}")
            return
        updated = existing.rstrip() + "\n\n" + AGENTS_BLOCK
        agents_path.write_text(updated, encoding="utf-8")
        print(f"[codex] appended TrinitySafe block to AGENTS.md: {agents_path}")
        return

    agents_path.write_text(AGENTS_BLOCK, encoding="utf-8")
    print(f"[codex] created AGENTS.md with TrinitySafe block: {agents_path}")


def main() -> None:
    args = parse_args()
    source = resolve_source(args.source_skill_dir)
    targets = build_targets(args)
    project_root = resolve_project_root_for_agents(args.codex_base_dir)

    installed: List[Dict[str, Path]] = []
    for target in targets:
        dest = install_one(target["name"], target["base"], args.mode, source)
        installed.append({"name": target["name"], "dest": dest})

    if not args.skip_verify:
        for item in installed:
            run_verify(item["name"], item["dest"])

    ensure_agents_md(project_root)
    print("Install complete. Restart Codex to load new skills.")


if __name__ == "__main__":
    main()
