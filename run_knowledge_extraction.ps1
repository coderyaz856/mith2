# Ingest Knowledge from Articles
# Extracts structured knowledge from PDFs using Gemini LLM

$ErrorActionPreference = 'Stop'

# Gemini configuration
$env:LLM_PROVIDER = 'gemini'
$env:GEMINI_API_KEY = 'AIzaSyBu3T2GHt6HWHnPFcCJoFAhv-V2FiIdveo'
$env:MODEL_NAME = 'gemini-2.5-flash'
$env:LLM_MIN_INTERVAL_S = '5.0'

Write-Host "`n=== Knowledge Ingestion ===" -ForegroundColor Cyan
Write-Host "Provider: Gemini ($env:MODEL_NAME)" -ForegroundColor Yellow

# Run ingestion
python -m scripts.ingest_knowledge --articles-dir articles --output data/knowledge_base.json --max-chunks 3 --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Success! View results with:" -ForegroundColor Green
    Write-Host "  python -m scripts.ingest_knowledge --view data/knowledge_base.json" -ForegroundColor White
}
