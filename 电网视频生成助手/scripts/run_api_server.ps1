param(
    [string]$EnvName = "AICODING",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Reload
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
    $UvicornArgs = @(
        "run",
        "--no-capture-output",
        "-n",
        $EnvName,
        "python",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        $BindHost,
        "--port",
        $Port
    )

    if ($Reload) {
        $UvicornArgs += "--reload"
    }

    & conda @UvicornArgs
}
finally {
    Pop-Location
}
