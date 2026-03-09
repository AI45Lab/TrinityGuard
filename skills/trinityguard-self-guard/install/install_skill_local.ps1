param(
  [ValidateSet('codex','claude','both')]
  [string]$Target = 'both',

  [ValidateSet('copy','link')]
  [string]$Mode = 'copy',

  [string]$SourceSkillDir = '',
  [string]$CodexBaseDir = '',
  [string]$ClaudeBaseDir = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$defaultSource = Join-Path $repoRoot 'skills\trinityguard-self-guard'
$src = if ([string]::IsNullOrWhiteSpace($SourceSkillDir)) { $defaultSource } else { (Resolve-Path $SourceSkillDir).Path }

if (-not (Test-Path (Join-Path $src 'trinityguard-self-guard-orchestrator\SKILL.md'))) {
  throw "Invalid skill source dir: $src"
}

$codexBase = if ([string]::IsNullOrWhiteSpace($CodexBaseDir)) { Join-Path $env:USERPROFILE '.codex' } else { $CodexBaseDir }
$claudeBase = if ([string]::IsNullOrWhiteSpace($ClaudeBaseDir)) { Join-Path $env:USERPROFILE '.claude' } else { $ClaudeBaseDir }

function Install-One([string]$clientName, [string]$baseDir, [string]$mode, [string]$source) {
  $destRoot = Join-Path $baseDir 'skills'
  $dest = Join-Path $destRoot 'trinityguard-self-guard'

  New-Item -ItemType Directory -Force $destRoot | Out-Null
  if (Test-Path $dest) {
    Remove-Item -Recurse -Force $dest
  }

  if ($mode -eq 'copy') {
    Copy-Item -Recurse -Force $source $dest
  } else {
    New-Item -ItemType Junction -Path $dest -Target $source | Out-Null
  }

  Write-Host "[$clientName] installed: $dest"
}

$targets = @()
if ($Target -eq 'both') {
  $targets = @(
    @{ Name = 'codex'; Base = $codexBase },
    @{ Name = 'claude'; Base = $claudeBase }
  )
} elseif ($Target -eq 'codex') {
  $targets = @(@{ Name = 'codex'; Base = $codexBase })
} else {
  $targets = @(@{ Name = 'claude'; Base = $claudeBase })
}

foreach ($t in $targets) {
  Install-One -clientName $t.Name -baseDir $t.Base -mode $Mode -source $src
}

Write-Host 'Install complete. Restart target client(s) to load new skills.'
