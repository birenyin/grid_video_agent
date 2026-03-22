param(
    [string]$EnvName = "AICODING"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "conda was not found. Please make sure Anaconda or Miniconda is on PATH."
}

$env:CONDA_NO_PLUGINS = "true"
$env:PYTHONIOENCODING = "utf-8"

Push-Location $ProjectRoot
try {
    & conda run --no-capture-output -n $EnvName python -m src.grid_video_agent.healthcheck
}
finally {
    Pop-Location
}
