param(
  [ValidateSet('codex','claude','both')]
  [string]$Target = 'both',

  [ValidateSet('copy','link')]
  [string]$Mode = 'copy',

  [string]$SourceSkillDir = '',
  [string]$CodexBaseDir = '',
  [string]$ClaudeBaseDir = '',
  [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'

function Resolve-Python {
  $py = Get-Command python -ErrorAction SilentlyContinue
  if ($py) { return $py.Source }
  $py3 = Get-Command py -ErrorAction SilentlyContinue
  if ($py3) { return "$($py3.Source) -3" }
  throw "Python not found. Install Python and ensure `python` or `py` is in PATH."
}

$python = Resolve-Python
$script = Join-Path $PSScriptRoot 'install_skill_local.py'

$argsList = @($script, '--target', $Target, '--mode', $Mode)
if (-not [string]::IsNullOrWhiteSpace($SourceSkillDir)) { $argsList += @('--source-skill-dir', $SourceSkillDir) }
if (-not [string]::IsNullOrWhiteSpace($CodexBaseDir)) { $argsList += @('--codex-base-dir', $CodexBaseDir) }
if (-not [string]::IsNullOrWhiteSpace($ClaudeBaseDir)) { $argsList += @('--claude-base-dir', $ClaudeBaseDir) }
if ($SkipVerify) { $argsList += '--skip-verify' }

if ($python.Contains(' -3')) {
  & py -3 @argsList
} else {
  & $python @argsList
}
