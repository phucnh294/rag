<#
Test the Ollama /api/generate endpoint.

Usage:
  .\test-generate.ps1
  .\test-generate.ps1 -Model "gemma:2b" -Prompt "Hello"
#>
param(
    [string]$BaseUrl = "http://localhost:11434",
    [string]$Model = "llama3.1:latest",
    [string]$Prompt = "Viết hàm tính giai thừa bằng Python"
)

$body = @{
    model   = $Model
    prompt  = $Prompt
    stream  = $false
    options = @{
        temperature = 0.2
        top_k       = 20
        top_p       = 0.5
    }
} | ConvertTo-Json -Depth 5

Write-Host "POST $BaseUrl/api/generate (model=$Model)"

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
} catch {
    Write-Error "FAIL: request error - $_"
    exit 1
}

$pass = $true

if (-not $response.response -or $response.response.Trim().Length -eq 0) {
    Write-Error "FAIL: 'response' field is empty"
    $pass = $false
}

if ($response.done -ne $true) {
    Write-Error "FAIL: 'done' is not true"
    $pass = $false
}

if ($response.model -ne $Model) {
    Write-Warning "Response model '$($response.model)' differs from requested '$Model'"
}

if ($pass) {
    Write-Host "PASS" -ForegroundColor Green
    Write-Host "---- Response ----"
    Write-Host $response.response
    exit 0
} else {
    exit 1
}
