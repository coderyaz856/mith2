# Quick script to run a query and open live view
Write-Host "Starting research query..." -ForegroundColor Cyan

$body = @{
    topic = "How do mobile devices support language learning?"
    max_turns = 2
    consensus_threshold = 0.8
} | ConvertTo-Json

try {
    # Start the run
    $resp = Invoke-RestMethod -Uri http://localhost:8080/run -Method Post -Body $body -ContentType 'application/json'
    $runId = $resp.run_id
    
    Write-Host "Run started: $runId" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting for run to complete..." -ForegroundColor Yellow
    
    # Wait for run to complete
    Start-Sleep -Seconds 15
    
    Write-Host "Opening ANIMATED replay in browser..." -ForegroundColor Cyan
    
    # Open browser with the animated view
    $url = "http://localhost:8080/graph/animated/$runId"
    Start-Process $url
    
    Write-Host "Browser opened: $url" -ForegroundColor Green
    Write-Host ""
    Write-Host "Click PLAY to watch the agent conversation flow!" -ForegroundColor Cyan
}
catch {
    Write-Host "Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

