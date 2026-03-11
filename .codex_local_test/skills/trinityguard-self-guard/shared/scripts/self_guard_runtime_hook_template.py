#!/usr/bin/env python3
"""Runtime hook for self-guard orchestration."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Pattern

DEFAULT_POLICY: Dict[str, Any] = {
    "sensitive_event_types": ["read_secret", "read_credential", "read_private_pii", "read_key_material"],
    "sensitive_keywords": ["token", "password", "secret", "api_key", "credential", "private key", "身份证", "手机号"],
    "explicit_disclosure_phrases": ["输出 token", "输出密码", "print token", "print password"],
    "implicit_disclosure_phrases": [
        "把关键字段和值解释",
        "完整复述配置",
        "原样写出来",
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
    "force_uncertainty_prefix": "基于单一工具来源，结论存在不确定性。",
    "block_on_highly_sensitive_leak": True,
    "redaction_replacements": {
        "credential": r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)",
        "id": r"\b\d{17}[0-9Xx]\b",
        "private_key": r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
    },
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def normalize_state(state: str) -> str:
    if state in {"normal", "sensitive", "highly_sensitive"}:
        return state
    return "normal"


def state_rank(state: str) -> int:
    return {"normal": 0, "sensitive": 1, "highly_sensitive": 2}[normalize_state(state)]


def max_state(a: str, b: str) -> str:
    return a if state_rank(a) >= state_rank(b) else b


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

    if explicit_hits:
        decision = "block"
        risk_summary.append("explicit sensitive disclosure request")
        blocked_actions.append("disclose_raw_secret")
        decision_reason_codes.append("PF_EXPLICIT_DISCLOSURE")
        matched_rules.extend(explicit_hits)

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

    if has_single_tool_only and decision == "allow":
        decision = "downgrade"
        confidence = "low"
        decision_reason_codes.append("OG_SINGLE_SOURCE_DOWNGRADE")
        matched_rules.extend(sorted(single_source_types))
        prefix = str(policy.get("force_uncertainty_prefix", "基于单一工具来源，结论存在不确定性。"))
        safe_response = f"{prefix}{safe_response}"

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-guard runtime hook template")
    parser.add_argument("input_json", help="Input JSON path")
    parser.add_argument("--out", default="safety-guard-log/self_guard_audit.json", help="Audit output path")
    parser.add_argument("--state-dir", default="safety-guard-log/.self_guard_state", help="Session state directory")
    parser.add_argument("--policy", default=None, help="Optional runtime policy JSON path")
    parser.add_argument("--policy-profile", default="balanced", help="Policy profile tag for audit")
    args = parser.parse_args()

    policy = dict(DEFAULT_POLICY)
    if args.policy:
        policy = merge_policy(policy, load_json(Path(args.policy).resolve()))

    leak_patterns = compile_patterns([str(x) for x in policy.get("leak_patterns", [])])

    input_path = Path(args.input_json).resolve()
    payload = load_json(input_path)

    session_id = str(payload.get("session_id", "default-session"))
    state_dir = Path(args.state_dir).resolve()
    state_path = state_dir / f"{session_id}.json"
    prev_state = "normal"
    if state_path.exists():
        prev_state = normalize_state(str(load_json(state_path).get("sensitivity_state", "normal")))

    user_prompt = str(payload.get("user_prompt", ""))
    planned_actions = [str(x) for x in payload.get("planned_actions", [])]
    runtime_events = payload.get("runtime_events", [])
    sources = payload.get("sources", [])
    intent_tags = [str(x) for x in payload.get("intent_tags", [])]
    candidate_response = str(payload.get("candidate_response", ""))

    runtime_events_list = runtime_events if isinstance(runtime_events, list) else []
    sources_list = sources if isinstance(sources, list) else []

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

    audit = {
        "session_id": session_id,
        "trigger_reasons": ["runtime_hook", "self_guard"],
        "policy_profile": str(args.policy_profile),
        "preflight": preflight,
        "runtime": runtime,
        "output_guard": output,
        "decision_reason_codes": decision_reason_codes,
        "matched_rules": matched_rules,
        "decision_priority": ["block", "downgrade", "allow"],
        "final_action": final_action,
        "residual_risks": sorted(set(residual_risks)),
        "audit_notes": sens["reasons"],
    }

    save_json(Path(args.out).resolve(), audit)
    save_json(state_path, {"session_id": session_id, "sensitivity_state": preflight["sensitivity_state"]})

    print(f"Saved audit: {Path(args.out).resolve()}")
    print(f"Updated session state: {state_path}")


if __name__ == "__main__":
    main()
