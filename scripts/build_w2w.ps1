param(
    [switch] $SkipDependencyCheck
)

<#
Builds dist/w2w.exe from w2w.spec, using the project's own .venv (not system Python) -
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

if (-not (Test-Path $venvPython)) {
    Write-Error "Project .venv not found at $venvPython. Create it first (e.g. 'uv sync')."
    exit 2
}

if (-not $SkipDependencyCheck) {
    & $venvPython -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller not found in .venv - installing it there (build tool only, not a project dependency)..."
        $uv = Get-Command uv -ErrorAction SilentlyContinue
        if ($uv) {
            & uv pip install --python $venvPython pyinstaller
        } else {
            & $venvPython -m pip install pyinstaller
        }
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

$exePath = Join-Path $repoRoot "dist\w2w.exe"
if ($buildExitCode -ne 0 -or -not (Test-Path $exePath)) {
    Write-Error "Build failed - dist\w2w.exe was not produced."
    exit 1
}

Write-Host "Build succeeded: $exePath"
