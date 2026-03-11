param(
  [ValidateSet('codex','claude')]
  [string]$Target = 'codex',
  [string]$BaseDir = '',
  [string]$SkillDir = '',
  [string]$PolicyProfile = 'balanced',
  [string]$PolicyFile = ''
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
$script = Join-Path $PSScriptRoot 'verify_install.py'

$argsList = @($script, '--target', $Target, '--policy-profile', $PolicyProfile)
if (-not [string]::IsNullOrWhiteSpace($BaseDir)) { $argsList += @('--base-dir', $BaseDir) }
if (-not [string]::IsNullOrWhiteSpace($SkillDir)) { $argsList += @('--skill-dir', $SkillDir) }
if (-not [string]::IsNullOrWhiteSpace($PolicyFile)) { $argsList += @('--policy-file', $PolicyFile) }

if ($python.Contains(' -3')) {
  & py -3 @argsList
} else {
  & $python @argsList
}
