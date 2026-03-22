param(
    [Parameter(Mandatory = $true)]
    [string]$JobId,
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$Endpoint = "$($BaseUrl.TrimEnd('/'))/automation/jobs/$JobId/run"
Write-Host "POST $Endpoint"

$Response = Invoke-RestMethod -Method Post -Uri $Endpoint
$Response | ConvertTo-Json -Depth 6
