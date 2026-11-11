param(
    [switch] $SkipDependencyCheck
)

<#
Ensures the project .venv exists and is in sync ('uv sync'), then builds dist/WinUI_to_WebUI.exe
from w2w.spec, using the project's own .venv (not system Python) -
that .venv holds the real runtime dependencies (aimmspy, lxml, pandas, PySide6, ...).
Building with a Python that lacks aimmspy produces an exe that fails every conversion
with "ModuleNotFoundError: No module named 'aimmspy'" at run time, without PyInstaller
ever reporting an error at build time.

This script does not clean build/ or dist/ itself - run .\scripts\clean_w2w.ps1 first
for a from-scratch build.

Usage:
  .\scripts\build_w2w.ps1
  .\scripts\build_w2w.ps1 -SkipDependencyCheck  # skip the PyInstaller-in-.venv check
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Error "uv not found on PATH. Install it from https://docs.astral.sh/uv/ so the project .venv can be created."
    exit 2
}

# Ensure the project .venv exists and matches pyproject.toml / uv.lock. A no-op when
# already in sync. --inexact keeps PyInstaller, which is installed below as a build-only tool.
Push-Location $repoRoot
try {
    & uv sync --inexact
    $syncExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($syncExitCode -ne 0 -or -not (Test-Path $venvPython)) {
    Write-Error "'uv sync' failed - could not set up the project .venv at $venvPython."
    exit 2
}

if (-not $SkipDependencyCheck) {
    & $venvPython -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller not found in .venv - installing it there (build tool only, not a project dependency)..."
        & uv pip install --python $venvPython pyinstaller
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install PyInstaller into .venv."
            exit 2
        }
    }
}

Push-Location $repoRoot
try {
    & $venvPython -m PyInstaller w2w.spec --noconfirm
    $buildExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

$exePath = Join-Path $repoRoot "dist\WinUI_to_WebUI.exe"
if ($buildExitCode -ne 0 -or -not (Test-Path $exePath)) {
    Write-Error "Build failed - dist\WinUI_to_WebUI.exe was not produced."
    exit 1
}

Write-Host "Build succeeded: $exePath"
