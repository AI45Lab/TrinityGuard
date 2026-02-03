"""Static security scan for Claude Skills (local directories).

This is an internal implementation inspired by common "skill security scan" ideas:
  - Parse a skill directory
  - Scan relevant files (SKILL.md, scripts, configs) for risky patterns
  - Produce a structured report with findings, risk score and level

It is intentionally lightweight and offline (no network calls).
"""

from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Sequence, Tuple

import yaml


SEVERITY_ORDER: Dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "WARNING": 2,
    "INFO": 3,
}


DEFAULT_SCAN_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".sh",
    ".bash",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
}


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".pytest_cache",
}


DEFAULT_ALLOWED_DOMAINS = [
    "api.anthropic.com",
    "github.com",
    "pypi.org",
    "npmjs.com",
]


DEFAULT_RULES_YAML = """
network_rules:
  - id: NET001
    name: "External network request"
    severity: CRITICAL
    patterns:
      - "curl\\\\s+.*http"
      - "wget\\\\s+"
      - "requests\\\\.(post|get|put|delete)\\\\("
      - "urllib\\\\.(request|parse)"
      - "httpx\\\\."
      - "fetch\\\\("
    description: "Potential outbound network requests"
    allowed_domains:
      - "api.anthropic.com"
      - "github.com"
      - "pypi.org"
      - "npmjs.com"

  - id: NET002
    name: "Data exfiltration"
    severity: CRITICAL
    patterns:
      - "curl.*-d.*@"
      - "wget.*--post-data"
      - "nc\\\\s+.*-l"
      - "netcat.*-l"
    description: "Potential data exfiltration patterns"

file_rules:
  - id: FILE001
    name: "Sensitive file access"
    severity: CRITICAL
    patterns:
      - "~?/\\\\.ssh/"
      - "~?/\\\\.env"
      - "~?/\\\\.aws/"
      - "~?/\\\\.azure/"
      - "~?/\\\\.credentials"
      - "\\\\.(pem|key)\\\\b"
      - "\\\\bid_rsa\\\\b"
      - "\\\\bid_ed25519\\\\b"
      - "credentials\\\\.json"
      - "secrets\\\\.(yaml|yml|json|env)"
      - "\\\\bpassword\\\\b"
      - "\\\\btoken\\\\b"
      - "api[_-]?key"
    description: "Attempts to access sensitive files or secrets"

  - id: FILE002
    name: "Dangerous file operations"
    severity: CRITICAL
    patterns:
      - "rm\\\\s+-rf\\\\s+/"
      - "chmod\\\\s+777"
      - "chmod\\\\s+a\\\\+rwx"
      - "\\\\bdd\\\\s+.*of=/"
      - ">\\\\s+/(etc|usr|bin|sbin)/"
    description: "Potentially destructive file operations"

command_rules:
  - id: CMD001
    name: "Dangerous command execution"
    severity: CRITICAL
    patterns:
      - "\\\\bsudo\\\\b"
      - "\\\\bsu\\\\s"
      - "rm\\\\s+-rf\\\\s+/"
      - "chmod\\\\s+777"
      - "\\\\bdd\\\\s+.*of=/"
      - ":\\\\(\\\\)>(\\\\s*)?\\\\("
    description: "Commands that may compromise the system"

  - id: CMD002
    name: "System command invocation"
    severity: WARNING
    patterns:
      - "\\\\bos\\\\.system\\\\s*\\\\("
      - "subprocess\\\\.(call|run|Popen).*shell\\\\s*=\\\\s*True"
      - "\\\\bexec\\\\s*\\\\("
      - "\\\\bpopen\\\\s*\\\\("
    description: "Use of APIs that execute system commands"

injection_rules:
  - id: INJ002
    name: "Dynamic code execution"
    severity: WARNING
    patterns:
      - "\\\\beval\\\\s*\\\\("
      - "\\\\bexec\\\\s*\\\\("
      - "__import__\\\\s*\\\\("
      - "\\\\bcompile\\\\s*\\\\("
    description: "Dynamic code execution patterns"

  - id: INJ003
    name: "Backdoor patterns"
    severity: CRITICAL
    patterns:
      - "bash\\\\s+-i\\\\s+>&\\\\s*/dev/tcp/"
      - "nc\\\\s+-.*-e\\\\s+/"
      - "netcat.*-e"
    description: "Known backdoor / reverse shell patterns"

dependency_rules:
  - id: DEP001
    name: "Global package install"
    severity: WARNING
    patterns:
      - "pip\\\\s+install.*--global"
      - "npm\\\\s+install.*-g"
      - "npm\\\\s+i.*-g"
      - "yarn\\\\s+global"
      - "gem\\\\s+install"
    description: "Global installs may impact other projects"

  - id: DEP002
    name: "Force upgrade / overwrite"
    severity: WARNING
    patterns:
      - "--upgrade"
      - "--force-reinstall"
      - "--ignore-installed"
    description: "Forced upgrades may break environments"

obfuscation_rules:
  - id: OBF001
    name: "Obfuscation"
    severity: WARNING
    patterns:
      - "base64\\\\.decode"
      - "base64\\\\.b64decode"
      - "chr\\\\s*\\\\(.+\\\\)\\\\s*\\\\+\\\\s*chr"
      - "exec\\\\s*\\\\(.*decode"
    description: "Potential code obfuscation patterns"

  - id: OBF002
    name: "Indirect invocation"
    severity: WARNING
    patterns:
      - "__import__.*\\\\[.*\\\\]"
      - "getattr\\\\s*\\\\(.*\\\\s*,\\\\s*['\\\"].*['\\\"]\\\\s*\\\\)\\\\s*\\\\("
      - "vars\\\\(\\\\)\\\\[.*\\\\]"
    description: "Indirect calls that may hide intent"
"""


@dataclass(frozen=True)
class SkillScanRule:
    id: str
    name: str
    severity: str
    patterns: Tuple[str, ...]
    description: str
    allowed_domains: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillScanFinding:
    rule_id: str
    severity: str
    file: str
    line: int
    pattern: str
    description: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "pattern": self.pattern,
            "description": self.description,
            "confidence": self.confidence,
        }


def _normalize_severity(value: str) -> str:
    value = (value or "").strip().upper()
    if value in SEVERITY_ORDER:
        return value
    # Allow common synonyms
    if value in {"WARN", "WARNING"}:
        return "WARNING"
    if value in {"CRIT", "CRITICAL"}:
        return "CRITICAL"
    if value in {"HIGH"}:
        return "HIGH"
    return "INFO"


def _severity_at_least(severity: str, minimum: str) -> bool:
    sev = _normalize_severity(severity)
    min_sev = _normalize_severity(minimum)
    return SEVERITY_ORDER.get(sev, 99) <= SEVERITY_ORDER.get(min_sev, 99)


def _load_default_rules() -> List[SkillScanRule]:
    data = yaml.safe_load(DEFAULT_RULES_YAML) or {}
    return _parse_rules_config(data)


def _parse_rules_config(data: Dict[str, Any]) -> List[SkillScanRule]:
    rules: List[SkillScanRule] = []
    for category, rule_list in (data or {}).items():
        if not isinstance(rule_list, list):
            continue
        for item in rule_list:
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("id", "")).strip()
            if not rule_id:
                continue
            rules.append(
                SkillScanRule(
                    id=rule_id,
                    name=str(item.get("name", rule_id)),
                    severity=_normalize_severity(str(item.get("severity", "INFO"))),
                    patterns=tuple(str(p) for p in (item.get("patterns") or []) if str(p).strip()),
                    description=str(item.get("description", "")),
                    allowed_domains=tuple(
                        str(d).lower()
                        for d in (item.get("allowed_domains") or DEFAULT_ALLOWED_DOMAINS)
                        if str(d).strip()
                    )
                    if rule_id.startswith("NET")
                    else (),
                )
            )
    return rules


def load_rules_from_file(path: str) -> List[SkillScanRule]:
    """Load rules from a YAML file."""
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Rules file not found: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return _parse_rules_config(data)


def _compile_rules(rules: Sequence[SkillScanRule]) -> List[Tuple[SkillScanRule, Tuple[Pattern[str], ...]]]:
    compiled: List[Tuple[SkillScanRule, Tuple[Pattern[str], ...]]] = []
    for rule in rules:
        patterns: List[Pattern[str]] = []
        for p in rule.patterns:
            try:
                patterns.append(re.compile(p, re.IGNORECASE))
            except re.error:
                continue
        compiled.append((rule, tuple(patterns)))
    return compiled


def _calculate_confidence(line: str) -> float:
    confidence = 0.7
    if "#" in line or "//" in line:
        confidence -= 0.2

    suspicious_keywords = [
        "password",
        "secret",
        "token",
        "key",
        "credential",
        "eval",
        "exec",
        "system",
        "shell",
        "bash",
        "curl",
        "wget",
        "nc ",
        "netcat",
    ]
    line_lower = line.lower()
    if any(kw in line_lower for kw in suspicious_keywords):
        confidence += 0.2

    # Slight boost for especially sensitive locations
    if "~/.ssh" in line_lower or "id_rsa" in line_lower:
        confidence += 0.1

    return float(min(max(confidence, 0.0), 1.0))


def _collect_files(
    root: Path,
    *,
    scan_extensions: Optional[Sequence[str]] = None,
    exclude_dirs: Optional[Sequence[str]] = None,
    max_file_size_bytes: int = 512_000,
    max_files: int = 5_000,
) -> Tuple[List[Path], Dict[str, Any]]:
    scan_exts = set(scan_extensions) if scan_extensions else DEFAULT_SCAN_EXTENSIONS
    excluded = set(exclude_dirs) if exclude_dirs else DEFAULT_EXCLUDE_DIRS

    files: List[Path] = []
    meta = {
        "skipped_large_files": 0,
        "skipped_unreadable_files": 0,
        "skipped_non_target_files": 0,
    }

    def _maybe_add(path: Path):
        nonlocal files
        try:
            if path.name == "SKILL.md" or path.suffix in scan_exts:
                try:
                    size = path.stat().st_size
                    if max_file_size_bytes > 0 and size > max_file_size_bytes:
                        meta["skipped_large_files"] += 1
                        return
                except Exception:
                    pass
                files.append(path)
            else:
                meta["skipped_non_target_files"] += 1
        except Exception:
            meta["skipped_unreadable_files"] += 1

    if root.is_file():
        _maybe_add(root)
        return files, meta

    for current_root, dirs, filenames in os.walk(root):
        # Filter excluded directories in-place
        dirs[:] = [d for d in dirs if d not in excluded]

        for filename in filenames:
            path = Path(current_root) / filename
            _maybe_add(path)
            if len(files) >= max_files:
                return files, meta

    return files, meta


def _calculate_risk_score(findings: Sequence[SkillScanFinding]) -> float:
    weights = {"CRITICAL": 10, "HIGH": 7, "WARNING": 4, "INFO": 1}
    total = 0.0
    for f in findings:
        total += weights.get(_normalize_severity(f.severity), 1) * float(f.confidence)
    # Normalize to 0-10 assuming 20 critical findings is "max".
    max_score = 20 * 10 * 1.0
    score = (total / max_score) * 10 if max_score > 0 else 0.0
    return float(min(score, 10.0))


def _risk_level(score: float) -> str:
    if score >= 8:
        return "CRITICAL"
    if score >= 6:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    if score >= 2:
        return "LOW"
    return "SAFE"


def _default_scan_roots_if_empty(paths: Sequence[str]) -> List[str]:
    if paths:
        return list(paths)

    candidates: List[Path] = []
    home_skills = Path.home() / ".claude" / "skills"
    if home_skills.exists():
        candidates.append(home_skills)

    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.exists():
        candidates.append(cwd_skills)

    return [str(p) for p in candidates]


def scan_skill_paths(
    paths: Optional[Sequence[str]] = None,
    *,
    rules_file: Optional[str] = None,
    whitelist: Optional[Sequence[str]] = None,
    min_severity: str = "INFO",
    scan_extensions: Optional[Sequence[str]] = None,
    exclude_dirs: Optional[Sequence[str]] = None,
    max_file_size_bytes: int = 512_000,
    max_files: int = 5_000,
    max_issues: int = 1_000,
) -> Dict[str, Any]:
    """Scan one or more skill directories/files for risky patterns.

    Args:
        paths: Directories/files to scan. If empty, scans common default locations.
        rules_file: Optional YAML rules file (same schema as DEFAULT_RULES_YAML).
        whitelist: Optional list of rule IDs to ignore.
        min_severity: Only include findings at or above this severity.
        scan_extensions: File extensions to include.
        exclude_dirs: Directory names to exclude when walking.
        max_file_size_bytes: Skip files larger than this size.
        max_files: Stop after scanning this many files.
        max_issues: Stop after collecting this many issues.

    Returns:
        Dict report with fields: findings, summary, risk_score, risk_level, total_issues, total_files, scanned_paths.
    """
    min_severity = _normalize_severity(min_severity)
    whitelist_set = {str(x).strip() for x in (whitelist or []) if str(x).strip()}

    scan_roots = _default_scan_roots_if_empty(paths or [])
    if not scan_roots:
        raise ValueError("No scan paths provided and no default skill directories found.")

    rules = load_rules_from_file(rules_file) if rules_file else _load_default_rules()
    compiled_rules = _compile_rules(rules)

    all_files: List[Path] = []
    meta: Dict[str, Any] = {
        "skipped_large_files": 0,
        "skipped_unreadable_files": 0,
        "skipped_non_target_files": 0,
        "scanned_paths": [],
    }

    for p in scan_roots:
        root = Path(p).expanduser().resolve()
        meta["scanned_paths"].append(str(root))
        files, file_meta = _collect_files(
            root,
            scan_extensions=scan_extensions,
            exclude_dirs=exclude_dirs,
            max_file_size_bytes=max_file_size_bytes,
            max_files=max_files - len(all_files),
        )
        all_files.extend(files)
        for k, v in file_meta.items():
            meta[k] = meta.get(k, 0) + v
        if len(all_files) >= max_files:
            break

    findings: List[SkillScanFinding] = []

    for file_path in all_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            meta["skipped_unreadable_files"] += 1
            continue

        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if not line:
                continue

            for rule, patterns in compiled_rules:
                if rule.id in whitelist_set:
                    continue
                if not _severity_at_least(rule.severity, min_severity):
                    continue

                matched = False
                for pat in patterns:
                    if pat.search(line):
                        matched = True
                        break
                if not matched:
                    continue

                # Domain allowlist filter for NET rules
                if rule.allowed_domains:
                    line_lower = line.lower()
                    if any(domain in line_lower for domain in rule.allowed_domains):
                        continue

                findings.append(
                    SkillScanFinding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        file=str(file_path),
                        line=i,
                        pattern=line.strip()[:500],
                        description=rule.description,
                        confidence=_calculate_confidence(line),
                    )
                )

                if len(findings) >= max_issues:
                    break
            if len(findings) >= max_issues:
                break
        if len(findings) >= max_issues:
            break

    summary = {"CRITICAL": 0, "HIGH": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        sev = _normalize_severity(f.severity)
        summary[sev] = summary.get(sev, 0) + 1

    risk_score = _calculate_risk_score(findings)
    risk_level = _risk_level(risk_score)

    return {
        "scanned_paths": meta["scanned_paths"],
        "total_files": len(all_files),
        "findings": [f.to_dict() for f in findings],
        "summary": summary,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "total_issues": len(findings),
        "meta": {k: v for k, v in meta.items() if k != "scanned_paths"},
    }

