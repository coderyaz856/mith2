# Helper script to launch FastAPI server with env vars (edit before use)
# Usage:  .\start_server.ps1
# NOTE: Do NOT commit real secrets. Replace <YOUR_GROQ_KEY> first.

$ErrorActionPreference = 'Stop'

# --- Editable section -------------------------------------------------------
# Choose your provider: 'groq', 'grok', or 'gemini'
$env:LLM_PROVIDER = 'gemini'

# Set the appropriate API key for your chosen provider
# $env:GROQ_API_KEY = 'your_groq_key_here'
# $env:GROK_API_KEY = 'your_grok_key_here'
$env:GEMINI_API_KEY = 'AIzaSyBu3T2GHt6HWHnPFcCJoFAhv-V2FiIdveo'   # Replace with your Gemini API key

# Model name for your provider
# Groq: 'llama-3.3-70b-versatile', 'mixtral-8x7b-32768', etc.
# Grok: 'grok-beta'
# Gemini: 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-live', 'gemini-2.0-flash-exp'
$env:MODEL_NAME   = 'gemini-2.0-flash'   # Stable model; change if experimenting

$env:REQUIRE_PROVIDER = 'true'
$env:ENABLE_BM25 = 'true'
$env:BM25_FILES_DIR = 'articles'
# Optional tuning to reduce 429 rate limits
$env:LLM_RETRY_MAX = '5'
$env:LLM_RETRY_BASE_DELAY = '1.0'
$env:AGENT_STEP_DELAY_S = '0.5'      # delay between agent stages - FASTER!
$env:LLM_MIN_INTERVAL_S = '1.0'      # minimum seconds between provider calls (global) - FASTER!
# Debate is always on by default
$env:DEBATE_ENABLE = 'true'
$env:DEBATE_ROUNDS = '1'              # increase for deeper clarification rounds
# ----------------------------------------------------------------------------

Write-Host "Starting uvicorn with provider=$env:LLM_PROVIDER model=$env:MODEL_NAME require_provider=$env:REQUIRE_PROVIDER" -ForegroundColor Cyan

# Kill any existing process on port 8080 (optional)
$existing = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
if ($existing) {
  Write-Host "Stopping existing process on 8080: PID $existing" -ForegroundColor Yellow
  Stop-Process -Id $existing -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}

# Launch server in foreground
uvicorn api.server:app --host 0.0.0.0 --port 8080