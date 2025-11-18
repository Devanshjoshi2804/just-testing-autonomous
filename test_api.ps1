# ============================================================================
# AutoTest-RL API Demo Script
# ============================================================================

Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "🚀 AutoTest-RL API - Live Demo" -ForegroundColor Cyan
Write-Host "===============================================`n" -ForegroundColor Cyan

$baseUrl = "http://localhost:8000"

# Test 1: Health Check
Write-Host "[1/5] Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "✅ Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Environment: $($health.environment)" -ForegroundColor Gray
    Write-Host "   Version: $($health.version)`n" -ForegroundColor Gray
} catch {
    Write-Host "❌ Health check failed: $_`n" -ForegroundColor Red
    exit 1
}

# Test 2: Root Endpoint
Write-Host "[2/5] Testing Root Endpoint..." -ForegroundColor Yellow
try {
    $root = Invoke-RestMethod -Uri "$baseUrl/" -Method Get
    Write-Host "✅ Message: $($root.message)" -ForegroundColor Green
    Write-Host "   Version: $($root.version)" -ForegroundColor Gray
    Write-Host "   Docs: $baseUrl$($root.docs)`n" -ForegroundColor Gray
} catch {
    Write-Host "❌ Root endpoint failed: $_`n" -ForegroundColor Red
}

# Test 3: API Info (Debug endpoint)
Write-Host "[3/5] Testing API Info Endpoint..." -ForegroundColor Yellow
try {
    $info = Invoke-RestMethod -Uri "$baseUrl/api/v1/info" -Method Get
    Write-Host "✅ Configuration:" -ForegroundColor Green
    Write-Host "   Environment: $($info.environment)" -ForegroundColor Gray
    Write-Host "   LLM Provider: $($info.llm_provider)" -ForegroundColor Gray
    Write-Host "   LLM Model: $($info.llm_model)" -ForegroundColor Gray
    Write-Host "   Embedding Model: $($info.embedding_model)" -ForegroundColor Gray
    Write-Host "   RL Algorithm: $($info.rl_algorithm)" -ForegroundColor Gray
    Write-Host "   Max Retries: $($info.max_retries)" -ForegroundColor Gray
    Write-Host "   RAG Top K: $($info.rag_top_k)" -ForegroundColor Gray
    Write-Host "   Chunk Size: $($info.chunk_size)`n" -ForegroundColor Gray
} catch {
    Write-Host "⚠️  API info not available (may be disabled in non-debug mode)`n" -ForegroundColor Yellow
}

# Test 4: Container Stats
Write-Host "[4/5] Checking Docker Container..." -ForegroundColor Yellow
$container = docker ps --filter "name=ollama-manager" --format "{{.Status}}"
if ($container) {
    Write-Host "✅ Container Status: $container`n" -ForegroundColor Green
} else {
    Write-Host "❌ Container not running`n" -ForegroundColor Red
}

# Test 5: API Documentation
Write-Host "[5/5] Opening API Documentation..." -ForegroundColor Yellow
Write-Host "✅ Opening browser at $baseUrl/docs`n" -ForegroundColor Green
Start-Process "$baseUrl/docs"

# Summary
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "📊 Demo Summary" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "`n✨ AutoTest-RL API is running successfully!" -ForegroundColor Green
Write-Host "`n🔗 Available Endpoints:" -ForegroundColor White
Write-Host "   • Health Check:     $baseUrl/health" -ForegroundColor Cyan
Write-Host "   • API Root:         $baseUrl/" -ForegroundColor Cyan
Write-Host "   • API Info:         $baseUrl/api/v1/info" -ForegroundColor Cyan
Write-Host "   • Swagger Docs:     $baseUrl/docs" -ForegroundColor Cyan
Write-Host "   • ReDoc:            $baseUrl/redoc`n" -ForegroundColor Cyan

Write-Host "📚 Next Steps:" -ForegroundColor White
Write-Host "   1. Add API routes for document upload" -ForegroundColor Gray
Write-Host "   2. Implement test generation endpoints" -ForegroundColor Gray
Write-Host "   3. Add RL training endpoints" -ForegroundColor Gray
Write-Host "   4. Create ChromaDB integration" -ForegroundColor Gray
Write-Host "   5. Add Celery task queue`n" -ForegroundColor Gray

Write-Host "===============================================`n" -ForegroundColor Cyan
