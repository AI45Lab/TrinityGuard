#!/usr/bin/env python3
"""Runtime hook for TrinityGuard self-guard orchestration.

Primary output is JSONL event stream. Optional summary JSON can be written via --out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Pattern

DEFAULT_POLICY: Dict[str, Any] = {
    "sensitive_event_types": ["read_secret", "read_credential", "read_private_pii", "read_key_material"],
    "sensitive_keywords": ["token", "password", "secret", "api_key", "credential", "private key", "身份证", "手机号"],
    "explicit_disclosure_phrases": ["输出 token", "输出密码", "print token", "print password"],
    "implicit_disclosure_phrases": [
        "把关键字段和值解释",
        "完整复述配置",
        "原样写出",
        "show me the value",
        "include actual values",
    ],
    "explanation_leakage_phrases": ["解释用途并给出值", "解释时列出示例值", "for explanation include exact values"],
    "high_risk_actions": ["execute_command", "write_file", "batch_modify", "network_call"],
    "retry_threshold_downgrade": 3,
    "single_source_types": ["tool_single_source"],
    "leak_patterns": [
        r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+",
        r"(?i)-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
        r"\b\d{17}[0-9Xx]\b",
    ],
    "residual_leak_patterns": [
        r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*(?!\[REDACTED\])[^\s,;]+",
        r"(?i)-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
        r"\b\d{17}[0-9Xx]\b",
    ],
    "force_uncertainty_prefix": "基于单一工具来源，结论存在不确定性：",
    "block_on_highly_sensitive_leak": True,
    "redaction_replacements": {
        "credential": r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)",
        "id": r"\b\d{17}[0-9Xx]\b",
        "private_key": r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def merge_policy(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(default)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            inner = dict(merged[k])
            inner.update(v)
            merged[k] = inner
        else:
            merged[k] = v
    return merged


def compile_patterns(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p) for p in patterns]


def get_match_hits(text: str, phrases: List[str]) -> List[str]:
    low_text = text.lower()
    hits: List[str] = []
    for phrase in phrases:
        if str(phrase).lower() in low_text:
            hits.append(str(phrase))
    return sorted(set(hits))


def is_credential_exfil_request(prompt_low: str) -> bool:
    target_terms = [
        "api_key",
        "apikey",
        "access_token",
        "token",
        "password",
        "secret",
        "密钥",
        "令牌",
        "凭据",
        "口令",
        "密码",
    ]
    action_terms = [
        "找出",
        "提取",
        "给我",
        "输出",
        "列出",
        "打印",
        "返回",
        "read",
        "extract",
        "show",
        "print",
        "list",
        "dump",
        "find",
        "give me",
    ]
    has_target = any(t in prompt_low for t in target_terms)
    has_action = any(a in prompt_low for a in action_terms)
    return has_target and has_action


def is_refusal_response(text: str) -> bool:
    text_low = text.lower()
    refusal_markers = [
        "我不能帮助",
        "我不能协助",
        "不能提供",
        "无法提供",
        "不能帮忙",
        "i can't help",
        "i cannot help",
        "can't assist",
        "cannot assist",
        "won't help",
        "cannot provide",
    ]
    return any(m in text_low for m in refusal_markers)


def normalize_state(state: str) -> str:
    if state in {"normal", "sensitive", "highly_sensitive"}:
        return state
    return "normal"


def state_rank(state: str) -> int:
    return {"normal": 0, "sensitive": 1, "highly_sensitive": 2}[normalize_state(state)]


def max_state(a: str, b: str) -> str:
    return a if state_rank(a) >= state_rank(b) else b


def event_risk_level(decision: str) -> str:
    mapping = {
        "allow": "low",
        "continue": "low",
        "downgrade": "medium",
        "block": "high",
        "stop": "high",
        "error": "critical",
    }
    return mapping.get(decision, "low")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def excerpt(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def redact_text(text: str, replacements: Dict[str, str]) -> Dict[str, Any]:
    redacted = text
    redaction_summary: List[Dict[str, Any]] = []
    credential_pattern = replacements.get("credential", r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)")
    id_pattern = replacements.get("id", r"\b\d{17}[0-9Xx]\b")
    private_key_pattern = replacements.get("private_key", r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----")

    redacted, credential_count = re.subn(credential_pattern, r"\1=[REDACTED]", redacted)
    redacted, id_count = re.subn(id_pattern, "[REDACTED_ID]", redacted)
    redacted, key_count = re.subn(private_key_pattern, "[REDACTED_PRIVATE_KEY]", redacted)

    if credential_count:
        redaction_summary.append({"type": "credential", "count": credential_count})
    if id_count:
        redaction_summary.append({"type": "id", "count": id_count})
    if key_count:
        redaction_summary.append({"type": "private_key", "count": key_count})
    return {"text": redacted, "summary": redaction_summary}


def build_retention_snapshot(policy: Dict[str, Any], final_action: str, user_prompt: str, safe_response: str) -> Dict[str, Any]:
    user_redacted = redact_text(user_prompt, policy.get("redaction_replacements", {}))["text"]
    resp_redacted = redact_text(safe_response, policy.get("redaction_replacements", {}))["text"]
    base = {
        "user_prompt_hash": hash_text(user_prompt),
        "safe_response_hash": hash_text(safe_response),
        "user_prompt_length": len(user_prompt),
        "safe_response_length": len(safe_response),
    }
    if final_action == "allow":
        base["retention_level"] = "summary_only"
        base["user_prompt_preview"] = excerpt(user_redacted, 120)
        base["safe_response_preview"] = excerpt(resp_redacted, 120)
    elif final_action == "downgrade":
        base["retention_level"] = "evidence_compact"
        base["user_prompt_preview"] = excerpt(user_redacted, 300)
        base["safe_response_preview"] = excerpt(resp_redacted, 300)
    else:
        base["retention_level"] = "evidence_full_redacted"
        base["user_prompt_preview"] = excerpt(user_redacted, 800)
        base["safe_response_preview"] = excerpt(resp_redacted, 800)
    return base


def infer_sensitivity(prompt: str, events: List[Dict[str, Any]], previous_state: str, policy: Dict[str, Any]) -> Dict[str, Any]:
    state = normalize_state(previous_state)
    reasons: List[str] = []

    sensitive_keywords = [str(x).lower() for x in policy.get("sensitive_keywords", [])]
    sensitive_event_types = {str(x).lower() for x in policy.get("sensitive_event_types", [])}

    low_prompt = prompt.lower()
    if any(k in low_prompt for k in sensitive_keywords):
        state = max_state(state, "sensitive")
        reasons.append("prompt contains sensitive keyword")

    for e in events:
        event_type = str(e.get("type", "")).strip().lower()
        if event_type in sensitive_event_types:
            state = max_state(state, "highly_sensitive")
            reasons.append(f"runtime event {event_type} is highly sensitive")

    if not reasons:
        reasons.append("no new sensitivity signal")

    return {"sensitivity_state": state, "reasons": reasons}


def preflight_decision(
    user_prompt: str,
    planned_actions: List[str],
    intent_tags: List[str],
    sensitivity_state: str,
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    prompt_low = user_prompt.lower()
    high_risk_actions = {str(x) for x in policy.get("high_risk_actions", [])}
    explicit_phrases = [str(x).lower() for x in policy.get("explicit_disclosure_phrases", [])]
    implicit_phrases = [str(x).lower() for x in policy.get("implicit_disclosure_phrases", [])]
    explanation_phrases = [str(x).lower() for x in policy.get("explanation_leakage_phrases", [])]
    has_high_risk_action = any(a in high_risk_actions for a in planned_actions)

    risk_summary: List[str] = []
    blocked_actions: List[str] = []
    verification_requirements: List[str] = []
    decision_reason_codes: List[str] = []
    matched_rules: List[str] = []
    decision = "allow"

    explicit_hits = get_match_hits(prompt_low, explicit_phrases)
    implicit_hits = get_match_hits(prompt_low, implicit_phrases)
    explanation_hits = get_match_hits(prompt_low, explanation_phrases)
    credential_exfil = is_credential_exfil_request(prompt_low)

    if explicit_hits or credential_exfil:
        decision = "block"
        risk_summary.append("explicit sensitive disclosure request")
        blocked_actions.append("disclose_raw_secret")
        decision_reason_codes.append("PF_EXPLICIT_DISCLOSURE")
        matched_rules.extend(explicit_hits)
        if credential_exfil:
            risk_summary.append("credential exfiltration intent detected")
            decision_reason_codes.append("PF_CREDENTIAL_EXFIL_REQUEST")
            matched_rules.append("credential_exfil_intent")

    if implicit_hits or explanation_hits or "summary_from_sensitive_context" in intent_tags:
        risk_summary.append("implicit disclosure risk in explanation/summarization")
        verification_requirements.append("enforce output leakage check")
        decision_reason_codes.append("PF_IMPLICIT_DISCLOSURE_RISK")
        matched_rules.extend(implicit_hits)
        matched_rules.extend(explanation_hits)
        if decision != "block":
            decision = "downgrade"

    if has_high_risk_action:
        risk_summary.append("high-risk action planned")
        verification_requirements.append("require confirmation for high-risk actions")
        decision_reason_codes.append("PF_HIGH_RISK_ACTION")
        if decision != "block":
            decision = "downgrade"

    if sensitivity_state in {"sensitive", "highly_sensitive"}:
        verification_requirements.append("force output guard before final response")

    return {
        "risk_summary": risk_summary or ["no critical preflight risk"],
        "sensitivity_state": sensitivity_state,
        "allowed_actions": ["read_only", "summarize", "explain"],
        "blocked_actions": blocked_actions,
        "verification_requirements": sorted(set(verification_requirements)),
        "decision_reason_codes": sorted(set(decision_reason_codes)),
        "matched_rules": sorted(set(matched_rules)),
        "preflight_decision": decision,
    }


def runtime_decision(runtime_events: List[Dict[str, Any]], sources: List[Dict[str, Any]], policy: Dict[str, Any]) -> Dict[str, Any]:
    alerts: List[Dict[str, str]] = []
    suggested_actions: List[str] = []
    trust_annotations: List[Dict[str, str]] = []
    decision_reason_codes: List[str] = []
    matched_rules: List[str] = []

    decision = "continue"
    retry_threshold = int(policy.get("retry_threshold_downgrade", 3))
    single_source_types = {str(x) for x in policy.get("single_source_types", ["tool_single_source"])}

    retry_count = sum(1 for e in runtime_events if str(e.get("type", "")).strip().lower() == "retry")
    if retry_count >= retry_threshold:
        alerts.append({"severity": "warning", "message": "repeated retries observed"})
        suggested_actions.append("pause and inspect root cause")
        decision = "downgrade"
        decision_reason_codes.append("RT_RETRY_THRESHOLD")
        matched_rules.append(f"retry_count>={retry_threshold}")

    for s in sources:
        source_type = str(s.get("source_type", "tool_single_source"))
        confidence = str(s.get("confidence", "low"))
        trust_annotations.append(
            {
                "source_id": str(s.get("source_id", "unknown")),
                "source_type": source_type,
                "confidence": confidence,
                "reason": str(s.get("reason", "runtime source annotation")),
            }
        )

    source_types = {t["source_type"] for t in trust_annotations}
    if source_types and source_types.issubset(single_source_types):
        alerts.append({"severity": "warning", "message": "single tool source only"})
        suggested_actions.append("collect independent corroboration source")
        if decision == "continue":
            decision = "downgrade"
        decision_reason_codes.append("RT_SINGLE_SOURCE_ONLY")
        matched_rules.extend(sorted(source_types))

    if any(a.get("severity") == "critical" for a in alerts):
        decision = "stop"
        decision_reason_codes.append("RT_CRITICAL_ALERT_STOP")

    return {
        "runtime_events": runtime_events,
        "alerts": alerts,
        "suggested_actions": sorted(set(suggested_actions)),
        "trust_annotations": trust_annotations,
        "decision_reason_codes": sorted(set(decision_reason_codes)),
        "matched_rules": sorted(set(matched_rules)),
        "runtime_decision": decision,
    }


def detect_leakage(text: str, leak_patterns: List[Pattern[str]]) -> bool:
    return any(p.search(text) for p in leak_patterns)


def build_source_disclosure(
    trust_annotations: List[Dict[str, Any]],
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    title = str(policy.get("single_source_disclosure_title", "Source Disclosure (Single-Source)")).strip() or "Source Disclosure (Single-Source)"
    missing_hint = str(policy.get("single_source_missing_hint", "source metadata missing")).strip() or "source metadata missing"

    source_items: List[Dict[str, str]] = []
    for ann in trust_annotations:
        source_items.append(
            {
                "source_id": str(ann.get("source_id", "unknown")),
                "source_type": str(ann.get("source_type", "unknown")),
                "confidence": str(ann.get("confidence", "unknown")),
                "reason": str(ann.get("reason", "")),
            }
        )

    if not source_items:
        return {
            "source_items": [],
            "source_disclosure": f"\n\n{title}\n- {missing_hint}",
        }

    lines: List[str] = [f"\n\n{title}"]
    for item in source_items:
        lines.append(
            "- source_id={source_id}, source_type={source_type}, confidence={confidence}, reason={reason}".format(
                source_id=item["source_id"],
                source_type=item["source_type"],
                confidence=item["confidence"],
                reason=item["reason"] if item["reason"] else "n/a",
            )
        )

    return {
        "source_items": source_items,
        "source_disclosure": "\n".join(lines),
    }


def output_guard(
    candidate_response: str,
    sensitivity_state: str,
    trust_annotations: List[Dict[str, Any]],
    policy: Dict[str, Any],
    leak_patterns: List[Pattern[str]],
) -> Dict[str, Any]:
    leakage = detect_leakage(candidate_response, leak_patterns)
    single_source_types = {str(x) for x in policy.get("single_source_types", ["tool_single_source"])}
    has_single_tool_only = bool(trust_annotations) and all(
        str(a.get("source_type", "")) in single_source_types for a in trust_annotations
    )

    decision = "allow"
    confidence = "high"
    safe_response = candidate_response
    redaction_applied = False
    residual_leakage_detected = False
    redaction_summary: List[Dict[str, Any]] = []
    source_items: List[Dict[str, str]] = []
    source_disclosure = ""
    decision_reason_codes: List[str] = []
    matched_rules: List[str] = []

    if leakage:
        redaction_result = redact_text(candidate_response, policy.get("redaction_replacements", {}))
        safe_response = str(redaction_result["text"])
        redaction_summary = list(redaction_result["summary"])
        redaction_applied = safe_response != candidate_response
        decision_reason_codes.append("OG_LEAK_PATTERN_HIT")
        matched_rules.append("leak_patterns")
        if bool(policy.get("block_on_highly_sensitive_leak", True)) and sensitivity_state == "highly_sensitive":
            decision = "block"
            decision_reason_codes.append("OG_HIGHLY_SENSITIVE_BLOCK")
        else:
            decision = "downgrade"
            decision_reason_codes.append("OG_REDACT_AND_DOWNGRADE")
        confidence = "low"

        residual_patterns = compile_patterns([str(x) for x in policy.get("residual_leak_patterns", [])])
        residual_leakage_detected = detect_leakage(safe_response, residual_patterns or leak_patterns)
        if residual_leakage_detected:
            decision = "block"
            decision_reason_codes.append("OG_RESIDUAL_LEAK_BLOCK")

    if has_single_tool_only and decision == "allow" and not is_refusal_response(safe_response):
        decision = "downgrade"
        confidence = "low"
        decision_reason_codes.append("OG_SINGLE_SOURCE_DOWNGRADE")
        matched_rules.extend(sorted(single_source_types))
        prefix = str(policy.get("force_uncertainty_prefix", "Single-source evidence only; confidence is limited: "))
        disclosure = build_source_disclosure(trust_annotations, policy)
        source_items = disclosure["source_items"]
        source_disclosure = disclosure["source_disclosure"]
        safe_response = f"{prefix}{safe_response}{source_disclosure}"

    if sensitivity_state in {"sensitive", "highly_sensitive"} and decision == "allow":
        confidence = "medium"

    return {
        "leakage_detected": leakage,
        "residual_leakage_detected": residual_leakage_detected,
        "redaction_applied": redaction_applied,
        "redaction_summary": redaction_summary,
        "decision_reason_codes": sorted(set(decision_reason_codes)),
        "matched_rules": sorted(set(matched_rules)),
        "confidence_level": confidence,
        "safe_response": safe_response,
        "source_disclosure": source_disclosure,
        "source_items": source_items,
        "output_decision": decision,
    }


def decide_final_action(preflight: Dict[str, Any], runtime: Dict[str, Any], output: Dict[str, Any]) -> str:
    if preflight["preflight_decision"] == "block" or output["output_decision"] == "block":
        return "block"
    if runtime["runtime_decision"] == "stop":
        return "block"
    if (
        preflight["preflight_decision"] == "downgrade"
        or runtime["runtime_decision"] == "downgrade"
        or output["output_decision"] == "downgrade"
    ):
        return "downgrade"
    return "allow"


def emit_event(
    events_log: Optional[Path],
    trace_id: str,
    session_id: str,
    turn_id: str,
    policy_profile: str,
    event_type: str,
    decision: str,
    reason_codes: List[str],
    matched_rules: List[str],
    extra: Dict[str, Any],
) -> None:
    event = {
        "ts": now_iso(),
        "trace_id": trace_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "policy_profile": policy_profile,
        "event_type": event_type,
        "risk_level": event_risk_level(decision),
        "decision": decision,
        "reason_codes": sorted(set(reason_codes)),
        "matched_rules": sorted(set(matched_rules)),
    }
    event.update(extra)
    if events_log is not None:
        append_jsonl(events_log, event)



def resolve_project_root(payload: Dict[str, Any], input_path: Path) -> Path:
    for key in ["project_path", "project_root", "workspace_root", "repo_root"]:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return Path(val).expanduser().resolve()
    return Path.cwd().resolve()


def resolve_path_in_project(path_str: str, project_root: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p.resolve()
    return (project_root / p).resolve()

def sanitize_turn_id(turn_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", turn_id.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "unknown-turn"


def make_turn_dir_name(turn_id: str) -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{sanitize_turn_id(turn_id)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-guard runtime hook template")
    parser.add_argument("input_json", help="Input JSON path")
    parser.add_argument("--out", default="", help="Optional summary JSON output path")
    parser.add_argument("--events-log", default=".codex/logs/self_guard_events.jsonl", help="JSONL event log path (legacy mode)")
    parser.add_argument("--state-dir", default=".codex/logs/.self_guard_state", help="Session state directory")
    parser.add_argument("--log-layout", choices=["legacy", "turn_dir"], default="turn_dir", help="Log layout strategy")
    parser.add_argument("--turns-dir", default=".codex/logs/turns", help="Per-turn log root directory")
    parser.add_argument("--index-log", default=".codex/logs/index.jsonl", help="Lightweight per-turn index JSONL")
    parser.add_argument("--policy", default=None, help="Optional runtime policy JSON path")
    parser.add_argument("--policy-profile", default="balanced", help="Policy profile tag for audit")
    args = parser.parse_args()

    input_path = Path(args.input_json).resolve()
    hook_start = perf_counter()
    payload = load_json(input_path)
    project_root = resolve_project_root(payload, input_path)
    events_log = resolve_path_in_project(args.events_log, project_root)
    state_dir = resolve_path_in_project(args.state_dir, project_root)
    out_path = resolve_path_in_project(args.out, project_root) if args.out else None
    turns_dir = resolve_path_in_project(args.turns_dir, project_root)
    index_log = resolve_path_in_project(args.index_log, project_root)
    session_id = str(payload.get("session_id", "default-session"))
    turn_id = str(payload.get("turn_id", payload.get("request_id", "unknown-turn")))
    trace_id = f"{session_id}:{turn_id}:{uuid.uuid4().hex[:8]}"
    user_prompt = str(payload.get("user_prompt", payload.get("user_request", "")))
    planned_actions = [str(x) for x in payload.get("planned_actions", [])]
    runtime_events = payload.get("runtime_events", [])
    sources = payload.get("sources", [])
    intent_tags = [str(x) for x in payload.get("intent_tags", [])]
    candidate_response = str(payload.get("candidate_response", ""))
    runtime_events_list = runtime_events if isinstance(runtime_events, list) else []
    sources_list = sources if isinstance(sources, list) else []

    events_sink: Optional[Path] = events_log if args.log_layout == "legacy" else None
    turn_dir = turns_dir / make_turn_dir_name(turn_id)
    turn_input_path = turn_dir / "input.json"
    turn_result_path = turn_dir / "result.json"

    if args.log_layout == "turn_dir":
        save_json(
            turn_input_path,
            {
                "ts": now_iso(),
                "session_id": session_id,
                "turn_id": turn_id,
                "trace_id": trace_id,
                "project_root": str(project_root),
                "input_path": str(input_path),
                "payload": payload,
            },
        )

    emit_event(
        events_log=events_sink,
        trace_id=trace_id,
        session_id=session_id,
        turn_id=turn_id,
        policy_profile=str(args.policy_profile),
        event_type="hook_start",
        decision="allow",
        reason_codes=[],
        matched_rules=[],
        extra={
            "input_json": str(input_path),
            "project_root": str(project_root),
            "input_summary": {
                "user_prompt_length": len(user_prompt),
                "candidate_response_length": len(candidate_response),
                "planned_actions": planned_actions,
                "intent_tags": intent_tags,
                "runtime_event_count": len(runtime_events_list),
                "source_count": len(sources_list),
            },
        },
    )

    try:
        policy = dict(DEFAULT_POLICY)
        if args.policy:
            policy = merge_policy(policy, load_json(Path(args.policy).resolve()))

        leak_patterns = compile_patterns([str(x) for x in policy.get("leak_patterns", [])])

        state_path = state_dir / f"{session_id}.json"
        prev_state = "normal"
        if state_path.exists():
            prev_state = normalize_state(str(load_json(state_path).get("sensitivity_state", "normal")))


        sens = infer_sensitivity(user_prompt, runtime_events_list, prev_state, policy)
        preflight = preflight_decision(user_prompt, planned_actions, intent_tags, sens["sensitivity_state"], policy)
        runtime = runtime_decision(runtime_events_list, sources_list, policy)
        output = output_guard(candidate_response, preflight["sensitivity_state"], runtime["trust_annotations"], policy, leak_patterns)

        final_action = decide_final_action(preflight, runtime, output)

        residual_risks: List[str] = []
        if output["leakage_detected"]:
            residual_risks.append("privacy leakage risk observed")
        if any(a["source_type"] in set(policy.get("single_source_types", [])) for a in runtime["trust_annotations"]):
            residual_risks.append("single-source reliability risk")

        decision_reason_codes = sorted(
            set(preflight.get("decision_reason_codes", []))
            | set(runtime.get("decision_reason_codes", []))
            | set(output.get("decision_reason_codes", []))
        )
        matched_rules = sorted(
            set(preflight.get("matched_rules", []))
            | set(runtime.get("matched_rules", []))
            | set(output.get("matched_rules", []))
        )

        retention = build_retention_snapshot(policy, final_action, user_prompt, output["safe_response"])

        emit_event(
            events_sink,
            trace_id,
            session_id,
            turn_id,
            str(args.policy_profile),
            "preflight_result",
            preflight["preflight_decision"],
            preflight.get("decision_reason_codes", []),
            preflight.get("matched_rules", []),
            {
                "sensitivity_state": preflight["sensitivity_state"],
                "risk_summary": preflight["risk_summary"],
                "verification_requirements": preflight["verification_requirements"],
                "allowed_actions": preflight["allowed_actions"],
                "blocked_actions": preflight["blocked_actions"],
                "planned_actions": planned_actions,
            },
        )

        emit_event(
            events_sink,
            trace_id,
            session_id,
            turn_id,
            str(args.policy_profile),
            "runtime_result",
            runtime["runtime_decision"],
            runtime.get("decision_reason_codes", []),
            runtime.get("matched_rules", []),
            {
                "runtime_event_count": len(runtime_events_list),
                "runtime_event_types": sorted(
                    set(str(e.get("type", "unknown")).strip().lower() for e in runtime_events_list)
                ),
                "source_types": sorted(set(str(s.get("source_type", "unknown")) for s in sources_list)),
                "alerts": runtime["alerts"],
                "suggested_actions": runtime["suggested_actions"],
                "trust_annotations": runtime["trust_annotations"],
            },
        )

        emit_event(
            events_sink,
            trace_id,
            session_id,
            turn_id,
            str(args.policy_profile),
            "output_guard_result",
            output["output_decision"],
            output.get("decision_reason_codes", []),
            output.get("matched_rules", []),
            {
                "leakage_detected": output["leakage_detected"],
                "residual_leakage_detected": output["residual_leakage_detected"],
                "redaction_applied": output["redaction_applied"],
                "redaction_summary": output["redaction_summary"],
                "confidence_level": output["confidence_level"],
                "source_disclosure_present": bool(output.get("source_disclosure", "")),
                "source_count": len(output.get("source_items", [])),
                "safe_response_length": len(output["safe_response"]),
                "safe_response_preview": excerpt(output["safe_response"], 160),
            },
        )

        duration_ms = int((perf_counter() - hook_start) * 1000)

        emit_event(
            events_sink,
            trace_id,
            session_id,
            turn_id,
            str(args.policy_profile),
            "final_decision",
            final_action,
            decision_reason_codes,
            matched_rules,
            {
                "final_action": final_action,
                "residual_risks": sorted(set(residual_risks)),
                "audit_notes": sens["reasons"],
                "retention": retention,
                "decision_chain": {
                    "preflight_decision": preflight["preflight_decision"],
                    "runtime_decision": runtime["runtime_decision"],
                    "output_decision": output["output_decision"],
                },
                "duration_ms": duration_ms,
            },
        )

        emit_event(
            events_sink,
            trace_id,
            session_id,
            turn_id,
            str(args.policy_profile),
            "hook_end",
            final_action,
            decision_reason_codes,
            matched_rules,
            {"duration_ms": duration_ms},
        )

        save_json(state_path, {"session_id": session_id, "sensitivity_state": preflight["sensitivity_state"]})

        summary = {
            "session_id": session_id,
            "turn_id": turn_id,
            "trace_id": trace_id,
            "policy_profile": str(args.policy_profile),
            "final_action": final_action,
            "decision_reason_codes": decision_reason_codes,
            "matched_rules": matched_rules,
            "duration_ms": duration_ms,
            "decision_chain": {
                "preflight_decision": preflight["preflight_decision"],
                "runtime_decision": runtime["runtime_decision"],
                "output_decision": output["output_decision"],
            },
            "output_guard": {
                "output_decision": output["output_decision"],
                "redaction_summary": output["redaction_summary"],
                "safe_response": output["safe_response"],
                "source_disclosure": output.get("source_disclosure", ""),
                "source_items": output.get("source_items", []),
            },
        }

        if args.log_layout == "turn_dir":
            result_record = {
                "ts": now_iso(),
                "session_id": session_id,
                "turn_id": turn_id,
                "trace_id": trace_id,
                "policy_profile": str(args.policy_profile),
                "final_action": final_action,
                "duration_ms": duration_ms,
                "decision_chain": summary["decision_chain"],
                "decision_reason_codes": decision_reason_codes,
                "matched_rules": matched_rules,
                "residual_risks": sorted(set(residual_risks)),
                "sensitivity_state": preflight["sensitivity_state"],
                "safe_response_preview": excerpt(output["safe_response"], 200),
                "redaction_summary": output["redaction_summary"],
                "retention": retention,
                "input_path": str(turn_input_path),
                "turn_dir": str(turn_dir),
            }
            save_json(turn_result_path, result_record)
            append_jsonl(
                index_log,
                {
                    "ts": now_iso(),
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "trace_id": trace_id,
                    "policy_profile": str(args.policy_profile),
                    "final_action": final_action,
                    "reason_codes": decision_reason_codes,
                    "matched_rules": matched_rules,
                    "duration_ms": duration_ms,
                    "turn_dir": str(turn_dir),
                    "input_path": str(turn_input_path),
                    "result_path": str(turn_result_path),
                },
            )
            if out_path:
                save_json(out_path, summary)
                print(f"Saved summary: {out_path}")
            print(f"Turn dir: {turn_dir}")
            print(f"Result path: {turn_result_path}")
            print(f"Index log path: {index_log}")
            print(f"Updated session state: {state_path}")
        else:
            if out_path:
                save_json(out_path, summary)
                print(f"Saved summary: {out_path}")
            print(f"Appended events: {events_log}")
            print("Turn dir: legacy-mode-disabled")
            print(f"Result path: {out_path if out_path else 'legacy-summary-disabled'}")
            print(f"Index log path: {index_log} (not written in legacy mode)")
            print(f"Updated session state: {state_path}")
    except Exception as exc:  # pragma: no cover - defensive logging
        emit_event(
            events_sink,
            trace_id,
            session_id,
            turn_id,
            str(args.policy_profile),
            "hook_error",
            "error",
            ["HOOK_RUNTIME_ERROR"],
            [],
            {
                "error": str(exc),
                "duration_ms": int((perf_counter() - hook_start) * 1000),
            },
        )
        raise


if __name__ == "__main__":
    main()
