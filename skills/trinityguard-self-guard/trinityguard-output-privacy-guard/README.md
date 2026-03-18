# trinityguard-output-privacy-guard

Output-stage privacy guard.

## Purpose

- detect leakage in candidate output
- redact or block unsafe responses
- downgrade single-source conclusions and attach source disclosure

## Inputs

- candidate response text
- sensitivity state
- trust annotations

## Outputs

- `output_decision`
- `safe_response`
- `redaction_summary`
- `source_disclosure`
- `source_items`
