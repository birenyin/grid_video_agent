param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$FrontendRoot = Join-Path $ProjectRoot "frontend"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Please install Node.js 16+ and retry."
}

$env:npm_config_cache = Join-Path $ProjectRoot ".npm-cache"

Push-Location $FrontendRoot
try {
    if (-not (Test-Path (Join-Path $FrontendRoot "node_modules"))) {
        npm install
    }
    npm run build
}
finally {
    Pop-Location
}
