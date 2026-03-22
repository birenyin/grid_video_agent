param(
    [string]$EnvName = "AICODING",
    [string]$OutputDir = "data/output_web",
    [ValidateSet("official", "mixed")]
    [string]$SourceSet = "mixed",
    [int]$PerSourceLimit = 3,
    [int]$TotalFetchLimit = 8,
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
    "--output", $OutputDir,
    "--fetch-web",
    "--source-set", $SourceSet,
    "--per-source-limit", $PerSourceLimit.ToString(),
    "--total-fetch-limit", $TotalFetchLimit.ToString(),
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
