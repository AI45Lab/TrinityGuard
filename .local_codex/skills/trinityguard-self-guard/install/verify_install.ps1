param(
  [ValidateSet('codex','claude')]
  [string]$Target = 'codex',
  [string]$BaseDir = '',
  [string]$SkillDir = ''
)

$ErrorActionPreference = 'Stop'

$skillDirPath = ''
if (-not [string]::IsNullOrWhiteSpace($SkillDir)) {
  $skillDirPath = $SkillDir
} else {
  $base = if ([string]::IsNullOrWhiteSpace($BaseDir)) {
    if ($Target -eq 'codex') { Join-Path $env:USERPROFILE '.codex' } else { Join-Path $env:USERPROFILE '.claude' }
  } else {
    $BaseDir
  }
  $skillDirPath = Join-Path $base 'skills\trinityguard-self-guard'
}

if (-not (Test-Path $skillDirPath)) {
  throw "Skill not installed at: $skillDirPath"
}

$required = @(
  'SKILL.md',
  'trinityguard-self-guard-orchestrator\SKILL.md',
  'trinityguard-preflight-selfcheck\SKILL.md',
  'trinityguard-runtime-selfmonitor\SKILL.md',
  'trinityguard-output-privacy-guard\SKILL.md',
  'shared\scripts\self_guard_runtime_hook_template.py',
  'shared\references\runtime_policy.template.json'
)

foreach ($rel in $required) {
  $p = Join-Path $skillDirPath $rel
  if (-not (Test-Path $p)) {
    throw "Missing required file: $p"
  }
}

Write-Host "[OK] file structure verified: $skillDirPath"

python (Join-Path $skillDirPath 'shared\scripts\validate_eval_assets_consistency.py') $skillDirPath --strict

$logRoot = Join-Path $skillDirPath 'safety-guard-log'
$verifyDir = Join-Path $logRoot 'verify'
New-Item -ItemType Directory -Force $verifyDir | Out-Null

$inputJson = Join-Path $skillDirPath 'shared\scripts\runtime_hook_input_example.json'
$policyJson = Join-Path $skillDirPath 'shared\references\runtime_policy.template.json'
$auditJson = Join-Path $verifyDir 'runtime_hook_audit.json'
$stateDir = Join-Path $verifyDir '.self_guard_state'

python (Join-Path $skillDirPath 'shared\scripts\self_guard_runtime_hook_template.py') $inputJson --policy $policyJson --out $auditJson --state-dir $stateDir
python -c "import json,sys;d=json.load(open(sys.argv[1],'r',encoding='utf-8-sig'));print('[OK] final_action=',d['final_action']);print('[OK] output_decision=',d['output_guard']['output_decision'])" $auditJson

Remove-Item -Recurse -Force $verifyDir
Write-Host '[OK] runtime hook smoke test passed'
