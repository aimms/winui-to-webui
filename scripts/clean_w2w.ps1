<#
Removes build/ and dist/, so the next .\scripts\build_w2w.ps1 starts from scratch.

Usage:
  .\scripts\clean_w2w.ps1
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")

Write-Host "Cleaning build/ and dist/..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $repoRoot "build")
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $repoRoot "dist")
