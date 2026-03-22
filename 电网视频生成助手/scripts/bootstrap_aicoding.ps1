param(
    [string]$EnvName = "AICODING"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot "environment.yml"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "conda was not found. Please make sure Anaconda or Miniconda is on PATH."
}

$env:CONDA_NO_PLUGINS = "true"

Write-Host "Project Root: $ProjectRoot"
Write-Host "Target Env:   $EnvName"

Push-Location $ProjectRoot
try {
    & conda run -n $EnvName python --version *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Environment found. Updating dependencies..."
        & conda env update --name $EnvName --file $EnvFile --prune
    }
    else {
        Write-Host "Environment not found. Creating it now..."
        & conda env create --name $EnvName --file $EnvFile
    }
}
finally {
    Pop-Location
}
