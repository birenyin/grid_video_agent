param(
    [string]$EnvName = "AICODING",
    [string]$CaseFile = "data/cases/state_grid_intro_case.json"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    & conda run --no-capture-output -n $EnvName python .\scripts\run_stage1_case.py $CaseFile
}
finally {
    Pop-Location
}
