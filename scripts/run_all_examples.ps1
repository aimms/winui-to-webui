param(
    [string[]] $Examples = @(),
    [switch] $StopOnFailure,
    [string] $W2wExe = "",
    [int] $ThrottleLimit = 8
)

<#
Runs all example conversions by invoking `scripts/run_example.py` in a fresh Python process per example.

Usage:
  .\scripts\run_all_examples.ps1             # run all examples, up to $ThrottleLimit at a time
  .\scripts\run_all_examples.ps1 -Examples ex1,ex2   # run only ex1 and ex2
  .\scripts\run_all_examples.ps1 -ThrottleLimit 4    # run at most 4 examples concurrently
  .\scripts\run_all_examples.ps1 -StopOnFailure     # run sequentially, stop on first failure

Examples run in parallel (via `ForEach-Object -Parallel`, PowerShell 7+ required), up to
$ThrottleLimit at a time (default 8 - matches the number of concurrent AIMMS engine sessions the
license allows, leaving headroom below the license's actual limit of 10). Each example already
gets its own fresh `work/` folder copied from `input/`, so concurrent runs don't conflict.

-StopOnFailure falls back to running examples one at a time in order, stopping at the first
failure - "stop on first failure" doesn't map onto already-launched concurrent runs, so the two
modes are mutually exclusive.

Logs are written to `logs/<example>-YYYYMMDD-HHMMSS.txt`.

An example folder containing a `pagemarkers.txt` file (one WinUI page Name per line,
blank lines and lines starting with '#' ignored) is run as a sequence of separate
`w2w.exe --page <name>` invocations against the same work/ folder, in file order -
simulating a user manually converting one page at a time - instead of a single plain
`w2w.exe` full-conversion call.

An example folder containing a `callw2w.bat` is converted by running that batch file instead (from
the example folder) - so per-example
options such as `--colors` live in the example itself. This takes precedence over
`pagemarkers.txt`, and its `..\..\..\dist\w2w.exe` path means -W2wExe is ignored for it.
#>

Set-StrictMode -Version Latest

if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Error "This script uses 'ForEach-Object -Parallel', which requires PowerShell 7+. You're running $($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition)). Re-run it with pwsh instead of powershell, e.g.: pwsh -File .\scripts\run_all_examples.ps1 (or start a 'pwsh' session and run .\scripts\run_all_examples.ps1 from there)."
    exit 2
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$examplesDir = Join-Path $repoRoot "examples"
$logsDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $examplesDir)) {
    Write-Error "Examples directory not found: $examplesDir"
    exit 2
}

New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

# Locate w2w.exe
if ($W2wExe -eq "") { $W2wExe = Join-Path $repoRoot "dist\w2w.exe" }
if (-not (Test-Path $W2wExe)) {
    Write-Error "Executable not found: $W2wExe. Run 'pyinstaller w2w.spec' first."
    exit 2
}

# Python is still needed for --compare (example_utils)
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) { $python = $venvPython } else { $python = "python" }

$runner = Join-Path $scriptDir "run_example.py"
if (-not (Test-Path $runner)) {
    Write-Error "Runner script not found: $runner"
    exit 2
}

function Get-ExampleList {
    param([string[]] $filter)
    if ($filter -and $filter.Count -gt 0) {
        return $filter
    }
    $list = @()
    Get-ChildItem -Path $examplesDir -Directory | ForEach-Object {
        $ex = $_.Name
        $input_dir = Join-Path $_.FullName "input"
        $expected = Join-Path $_.FullName "expected"
        if ((Test-Path $input_dir) -and (Test-Path $expected)) { $list += $ex }
    }
    return $list
}

# Ensure $toRun is always an array so .Count is reliable
$toRun = @(Get-ExampleList -filter $Examples)
if ($toRun.Count -eq 0) {
    Write-Host "No examples to run. Provide names with -Examples or add example folders with input/expected."
    exit 0
}

# Shared per-example runner, defined once and reused both sequentially (-StopOnFailure) and inside
# each parallel runspace (via -InitializationScript, since only data - not functions - crosses into
# a parallel scriptblock via $using:).
$runExampleDef = {
    function Invoke-Example {
        param($ex, $examplesDir, $logsDir, $W2wExe, $python, $runner)

        $timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
        $logFile = Join-Path $logsDir "$($ex)-$timestamp.txt"
        Write-Host "Running example: $ex -> log: $logFile"

        try {
            # Prepare work directory
            $srcDir      = Join-Path $examplesDir $ex
            $inputDir    = Join-Path $srcDir "input"
            $workDir     = Join-Path $srcDir "work"
            $markersFile = Join-Path $srcDir "pagemarkers.txt"
            $callW2wBat  = Join-Path $srcDir "callw2w.bat"
            if (Test-Path $workDir) { Remove-Item -Recurse -Force $workDir }
            Copy-Item -Recurse $inputDir $workDir

            if (Test-Path $callW2wBat) {
                # The example's own callw2w.bat decides how w2w.exe is called (e.g. --colors). It runs
                # from the example folder, as when double-clicked. cmd's exit code is the batch
                # file's last command (its closing `cd ..`), not w2w.exe's, so detect a crash from
                # the log instead. cd inside cmd itself: a native process doesn't inherit
                # Push-Location's location in a ForEach-Object -Parallel runspace.
                cmd /c "cd /d `"$srcDir`" && .\callw2w.bat" 2>&1 | Tee-Object -FilePath $logFile | Out-Null
                $exit = 0
                if (Select-String -Path $logFile -Pattern 'Traceback \(most recent call last\)' -Quiet) { $exit = 1 }
            } else {
            # Run conversion via exe from the work directory
            Push-Location $workDir
            try {
                if (Test-Path $markersFile) {
                    # Single-page mode: one `w2w --page <name>` call per marker line, in order,
                    # against the same work directory - simulating separate manual invocations.
                    $pageNames = @(Get-Content $markersFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
                    $exit = 0
                    $first = $true
                    foreach ($pageName in $pageNames) {
                        if ($first) {
                            & $W2wExe '--page' $pageName 2>&1 | Tee-Object -FilePath $logFile | Out-Null
                            $first = $false
                        } else {
                            & $W2wExe '--page' $pageName 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Null
                        }
                        $exit = $LASTEXITCODE
                        if ($exit -ne 0) { break }
                    }
                } else {
                    & $W2wExe 2>&1 | Tee-Object -FilePath $logFile | Out-Null
                    $exit = $LASTEXITCODE
                }
            } finally {
                Pop-Location
            }
            }

            # Compare output against expected
            if ($exit -eq 0) {
                & $python $runner '--compare-only' $ex 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Null
                if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }
            }
        } catch {
            Write-Error "Execution failed for $($ex): $($_)"
            $exit = 1
        }

        if ($exit -ne 0) {
            Write-Host "Example failed: $ex (exit $exit)"
        } else {
            Write-Host "Example succeeded: $ex"
        }

        [pscustomobject]@{ Example = $ex; ExitCode = $exit; Log = $logFile }
    }
}

if ($StopOnFailure) {
    . $runExampleDef
    $results = @()
    foreach ($ex in $toRun) {
        $result = Invoke-Example -ex $ex -examplesDir $examplesDir -logsDir $logsDir -W2wExe $W2wExe -python $python -runner $runner
        $results += $result
        if ($result.ExitCode -ne 0) { break }
    }
} else {
    # ForEach-Object -Parallel has no -InitializationScript param, and $using: only crosses
    # variables (not functions) into the parallel runspace - so ship the function as source text
    # and (re-)define it at the top of each iteration instead.
    $runExampleSrc = $runExampleDef.ToString()
    $results = @($toRun | ForEach-Object -Parallel {
        Invoke-Expression $using:runExampleSrc
        Invoke-Example -ex $_ -examplesDir $using:examplesDir -logsDir $using:logsDir -W2wExe $using:W2wExe -python $using:python -runner $using:runner
    } -ThrottleLimit $ThrottleLimit)
}

$failures = @($results | Where-Object { $_.ExitCode -ne 0 })

if ($failures.Count -gt 0) {
    Write-Host "\nSummary: $($failures.Count) failures:" -ForegroundColor Yellow
    foreach ($f in $failures) {
        Write-Host " - $($f.Example): exit $($f.ExitCode). Log: $($f.Log)"
    }
    exit 1
} else {
    Write-Host "\nAll examples ran successfully." -ForegroundColor Green
    exit 0
}
