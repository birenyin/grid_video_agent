param(
    [string]$EnvName = "AICODING",
    [string]$InputPath = "data/input/rpa_raw_feed.json",
    [string]$OutputDir = "data/output_local",
    [ValidateSet("rule", "auto", "api")]
    [string]$Mode = "rule",
    [switch]$NoPreview
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "conda was not found. Please make sure Anaconda or Miniconda is on PATH."
}

$env:CONDA_NO_PLUGINS = "true"
$env:PYTHONIOENCODING = "utf-8"

$CliArgs = @(
    "-m", "src.grid_video_agent.cli",
    "--input", $InputPath,
    "--output", $OutputDir,
    "--mode", $Mode
)

if (-not $NoPreview) {
    $CliArgs += "--render-preview"
}

Push-Location $ProjectRoot
try {
    & conda run --no-capture-output -n $EnvName python @CliArgs
}
finally {
    Pop-Location
}
