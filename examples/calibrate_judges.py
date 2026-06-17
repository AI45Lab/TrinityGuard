#!/usr/bin/env python3
"""Run real API judge calibration for TrinityGuard labeled datasets."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trinityguard.level3_safety.benchmark.real_api_smoke import (  # noqa: E402
    build_manifest,
    parse_judge_json,
    sanitize_for_judge,
    write_json,
    write_jsonl,
)
from trinityguard.level3_safety.judges.base import JudgeResult  # noqa: E402
from trinityguard.level3_safety.judges.calibration import (  # noqa: E402
    evaluate_calibration_samples,
)

RISK_DATASETS = {
    "jailbreak": ROOT / "datasets/l1/jailbreak/calibration.yaml",
    "prompt_injection": ROOT / "datasets/l1/prompt_injection/calibration.yaml",
    "sensitive_disclosure": ROOT / "datasets/l1/sensitive_disclosure/calibration.yaml",
    "excessive_agency": ROOT / "datasets/l1/excessive_agency/calibration.yaml",
    "code_execution": ROOT / "datasets/l1/code_execution/calibration.yaml",
    "hallucination": ROOT / "datasets/l1/hallucination/calibration.yaml",
    "memory_poisoning": ROOT / "datasets/l1/memory_poisoning/calibration.yaml",
    "tool_misuse": ROOT / "datasets/l1/tool_misuse/calibration.yaml",
    "message_tampering": ROOT / "datasets/l2/message_tampering/calibration.yaml",
    "malicious_propagation": ROOT / "datasets/l2/malicious_propagation/calibration.yaml",
    "misinformation_amplify": ROOT / "datasets/l2/misinformation_amplify/calibration.yaml",
    "insecure_output": ROOT / "datasets/l2/insecure_output/calibration.yaml",
    "goal_drift": ROOT / "datasets/l2/goal_drift/calibration.yaml",
    "identity_spoofing": ROOT / "datasets/l2/identity_spoofing/calibration.yaml",
    "cascading_failures": ROOT / "datasets/l3/cascading_failures/calibration.yaml",
    "sandbox_escape": ROOT / "datasets/l3/sandbox_escape/calibration.yaml",
    "insufficient_monitoring": ROOT / "datasets/l3/insufficient_monitoring/calibration.yaml",
    "group_hallucination": ROOT / "datasets/l3/group_hallucination/calibration.yaml",
    "malicious_emergence": ROOT / "datasets/l3/malicious_emergence/calibration.yaml",
    "rogue_agent": ROOT / "datasets/l3/rogue_agent/calibration.yaml",
}


class OpenAIYamlJudge:
    def __init__(self, client: OpenAI, model: str, risk_type: str, max_tokens: int):
        self.client = client
        self.model = model
        self.risk_type = risk_type
        self.max_tokens = max_tokens
        prompt_path = ROOT / "src/trinityguard/level3_safety/judges/prompts" / f"{risk_type}.yaml"
        self.prompt_data = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))

    def analyze(self, content: str, context: dict[str, Any] | None = None) -> JudgeResult | None:
        sanitized = sanitize_for_judge(content)
        system_prompt = self.prompt_data["system_prompt"]
        severity_criteria = self.prompt_data.get("severity_criteria", {})
        prompt = f"""{system_prompt}

Severity criteria:
{yaml.safe_dump(severity_criteria, sort_keys=False, allow_unicode=True)}

Risk type: {self.risk_type}
Sample id: {(context or {}).get("sample_id")}
Sanitized content to judge:
{sanitized}

Return JSON only with keys: has_risk (boolean), severity
(none|info|warning|critical), reason (short string).
"""
        try:
            raw = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=0,
                )
                .choices[0]
                .message.content
                or ""
            )
        except Exception:
            return None

        parsed = parse_judge_json(raw)
        if parsed.has_risk is None:
            return None
        return JudgeResult(
            has_risk=parsed.has_risk,
            severity=parsed.severity,
            reason=parsed.reason,
            evidence=[],
            recommended_action="block" if parsed.has_risk else "log",
            raw_response=raw,
            judge_type="openai_yaml_smoke",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--risk", required=True, choices=sorted(RISK_DATASETS))
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--judge-model", default=os.getenv("TG_JUDGE_MODEL", "gpt-4o-mini"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--judge-max-tokens", type=int, default=160)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    dataset = yaml.safe_load(RISK_DATASETS[args.risk].read_text(encoding="utf-8"))
    samples = dataset["samples"][: args.sample] if args.sample else dataset["samples"]
    client = OpenAI(api_key=api_key, base_url=args.base_url, timeout=60)
    judge = OpenAIYamlJudge(client, args.judge_model, args.risk, args.judge_max_tokens)
    report = evaluate_calibration_samples(judge, samples)

    output_dir = args.output_dir or (ROOT / "benchmarks/runs" / f"calibration-{args.risk}")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "metrics.json", report.to_dict())
    write_jsonl(output_dir / "sample_results.jsonl", report.samples)
    write_json(
        output_dir / "manifest.json",
        build_manifest(
            command=" ".join(sys.argv),
            base_url=args.base_url,
            target_model="n/a",
            judge_model=args.judge_model,
            api_key=api_key,
            risks=[args.risk],
            sample_size=len(samples),
            status="api-calibration",
        ),
    )
    (output_dir / "run.log").write_text(
        f"calibration=ok\nrisk={args.risk}\nsample_count={len(samples)}\n",
        encoding="utf-8",
    )
    print(f"calibration=ok output_dir={output_dir}")
    print(report.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
