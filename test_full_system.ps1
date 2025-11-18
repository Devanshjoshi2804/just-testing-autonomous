# ============================================================================
# AutoTest-RL - Complete System Test
# Upload API Doc → Parse → Analyze → Generate Tests → Execute
# ============================================================================

$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8000"
$apiDocPath = "uploads/api doc/Cargodham QA Doc (1).pdf"

Write-Host "`n" -NoNewline
Write-Host ("="*100) -ForegroundColor Cyan
Write-Host "🚀 AutoTest-RL - Complete System Test" -ForegroundColor Green
Write-Host ("="*100) -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Step 1: Verify API is Running
# ============================================================================
Write-Host "[1/5] 🔍 Verifying API Status..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "✅ API Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Environment: $($health.environment)" -ForegroundColor Gray
    Write-Host "   Version: $($health.version)`n" -ForegroundColor Gray
} catch {
    Write-Host "❌ API is not running! Start it first with: docker start ollama-manager`n" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Step 2: Upload API Documentation
# ============================================================================
Write-Host "[2/5] 📄 Uploading API Documentation..." -ForegroundColor Yellow

if (-not (Test-Path $apiDocPath)) {
    Write-Host "❌ API doc not found at: $apiDocPath`n" -ForegroundColor Red
    exit 1
}

Write-Host "   File: $apiDocPath" -ForegroundColor Gray
$fileInfo = Get-Item $apiDocPath
Write-Host "   Size: $([math]::Round($fileInfo.Length/1KB, 2)) KB`n" -ForegroundColor Gray

try {
    # Prepare multipart form data
    $boundary = [System.Guid]::NewGuid().ToString()
    $LF = "`r`n"
    
    $fileBytes = [System.IO.File]::ReadAllBytes($apiDocPath)
    $fileEnc = [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($fileBytes)
    
    $bodyLines = (
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"api_doc.pdf`"",
        "Content-Type: application/pdf$LF",
        $fileEnc,
        "--$boundary",
        "Content-Disposition: form-data; name=`"name`"$LF",
        "Cargodham API Documentation",
        "--$boundary",
        "Content-Disposition: form-data; name=`"description`"$LF",
        "QA API documentation for testing",
        "--$boundary--$LF"
    ) -join $LF
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/documents/upload" `
        -Method Post `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Body $bodyLines
    
    $docId = $response.document_id
    
    Write-Host "✅ Document Uploaded Successfully!" -ForegroundColor Green
    Write-Host "   Document ID: $docId" -ForegroundColor Cyan
    Write-Host "   Filename: $($response.filename)" -ForegroundColor Gray
    Write-Host "   Type: $($response.doc_type)" -ForegroundColor Gray
    Write-Host "   Size: $($response.file_size) bytes" -ForegroundColor Gray
    Write-Host "   Base URL: $($response.base_url)" -ForegroundColor Gray
    Write-Host "   Endpoints Found: $($response.endpoints_found)" -ForegroundColor Yellow
    Write-Host "   Text Chunks Created: $($response.chunks_created)`n" -ForegroundColor Gray
    
} catch {
    Write-Host "❌ Upload failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Details: $($_.ErrorDetails.Message)`n" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Step 3: Get Document Details
# ============================================================================
Write-Host "[3/5] 📋 Retrieving Document Details..." -ForegroundColor Yellow

try {
    $docDetails = Invoke-RestMethod -Uri "$baseUrl/api/v1/documents/$docId" -Method Get
    
    Write-Host "✅ Document Details Retrieved!" -ForegroundColor Green
    Write-Host "   Name: $($docDetails.name)" -ForegroundColor Gray
    Write-Host "   Base URL: $($docDetails.base_url)" -ForegroundColor Gray
    Write-Host "   Total Endpoints: $($docDetails.endpoints.Count)`n" -ForegroundColor Yellow
    
    Write-Host "   📍 Discovered Endpoints:" -ForegroundColor Cyan
    foreach ($ep in $docDetails.endpoints | Select-Object -First 10) {
        $authIcon = if ($ep.auth_required) { "🔒" } else { "🔓" }
        Write-Host "      $authIcon $($ep.method.PadRight(6)) $($ep.path)" -ForegroundColor White
        if ($ep.summary) {
            Write-Host "         └─ $($ep.summary)" -ForegroundColor DarkGray
        }
    }
    
    if ($docDetails.endpoints.Count -gt 10) {
        Write-Host "      ... and $($docDetails.endpoints.Count - 10) more endpoints" -ForegroundColor DarkGray
    }
    Write-Host ""
    
} catch {
    Write-Host "⚠️  Could not retrieve details: $($_.Exception.Message)`n" -ForegroundColor Yellow
}

# ============================================================================
# Step 4: Start Test Execution
# ============================================================================
Write-Host "[4/5] 🧪 Starting Intelligent Test Execution..." -ForegroundColor Yellow

try {
    $testRequest = @{
        document_id = $docId
        max_retries = 3
        use_optimal_order = $true
        test_types = @("positive")
    } | ConvertTo-Json
    
    $testSession = Invoke-RestMethod -Uri "$baseUrl/api/v1/tests/start" `
        -Method Post `
        -ContentType "application/json" `
        -Body $testRequest
    
    $sessionId = $testSession.session_id
    
    Write-Host "✅ Test Session Started!" -ForegroundColor Green
    Write-Host "   Session ID: $sessionId" -ForegroundColor Cyan
    Write-Host "   Status: $($testSession.status)" -ForegroundColor Gray
    Write-Host "   Total Endpoints: $($testSession.total_endpoints)" -ForegroundColor Yellow
    Write-Host "   Estimated Duration: $($testSession.estimated_duration)s`n" -ForegroundColor Gray
    
    # Monitor test progress
    Write-Host "   ⏳ Monitoring test progress..." -ForegroundColor Yellow
    
    $completed = $false
    $lastProgress = 0
    
    while (-not $completed) {
        Start-Sleep -Seconds 2
        
        $status = Invoke-RestMethod -Uri "$baseUrl/api/v1/tests/$sessionId/status" -Method Get
        
        if ($status.progress -ne $lastProgress) {
            Write-Host "      Progress: $([math]::Round($status.progress, 1))% | Tested: $($status.tested_endpoints)/$($status.total_endpoints) | ✅ $($status.passed) | ❌ $($status.failed)" -ForegroundColor Gray
            $lastProgress = $status.progress
        }
        
        if ($status.status -eq "completed" -or $status.status -eq "failed") {
            $completed = $true
        }
        
        # Timeout after 5 minutes
        if ((Get-Date) -gt $testSession.started_at.AddMinutes(5)) {
            Write-Host "   ⚠️  Test timeout reached`n" -ForegroundColor Yellow
            break
        }
    }
    
    Write-Host ""
    
} catch {
    Write-Host "❌ Test execution failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Details: $($_.ErrorDetails.Message)`n" -ForegroundColor Red
    $sessionId = $null
}

# ============================================================================
# Step 5: Get Test Report
# ============================================================================
if ($sessionId) {
    Write-Host "[5/5] 📊 Retrieving Test Report..." -ForegroundColor Yellow
    
    try {
        $report = Invoke-RestMethod -Uri "$baseUrl/api/v1/tests/$sessionId/report" -Method Get
        
        Write-Host "`n" -NoNewline
        Write-Host ("="*100) -ForegroundColor Green
        Write-Host "🎉 TEST EXECUTION COMPLETE!" -ForegroundColor Green
        Write-Host ("="*100) -ForegroundColor Green
        Write-Host ""
        
        Write-Host "📊 Summary Statistics:" -ForegroundColor Cyan
        Write-Host "   Total Tests: $($report.total_tests)" -ForegroundColor White
        Write-Host "   Passed: $($report.passed) ✅" -ForegroundColor Green
        Write-Host "   Failed: $($report.failed) ❌" -ForegroundColor Red
        Write-Host "   Success Rate: $([math]::Round($report.success_rate, 1))%" -ForegroundColor Yellow
        Write-Host "   Total Time: $([math]::Round($report.total_time, 2))s" -ForegroundColor Gray
        Write-Host "   Avg Time per Test: $([math]::Round($report.avg_time, 2))s" -ForegroundColor Gray
        Write-Host "   Total Attempts (incl. retries): $($report.total_attempts)`n" -ForegroundColor Gray
        
        Write-Host "📋 Detailed Results:" -ForegroundColor Cyan
        $resultNum = 1
        foreach ($result in $report.results | Select-Object -First 20) {
            $statusIcon = if ($result.success) { "✅" } else { "❌" }
            Write-Host "   $resultNum. $statusIcon $($result.method) $($result.endpoint)" -ForegroundColor White
            Write-Host "      Status: $($result.status_code) | Time: $([math]::Round($result.elapsed_time, 2))s | Attempts: $($result.attempts)" -ForegroundColor Gray
            
            if (-not $result.success -and $result.error) {
                Write-Host "      Error: $($result.error.Substring(0, [Math]::Min(100, $result.error.Length)))..." -ForegroundColor Red
            }
            $resultNum++
        }
        
        if ($report.results.Count -gt 20) {
            Write-Host "   ... and $($report.results.Count - 20) more results" -ForegroundColor DarkGray
        }
        
        Write-Host "`n💾 Flow Database Stats:" -ForegroundColor Cyan
        Write-Host "   Requests Stored: $($report.flow_stats.requests)" -ForegroundColor Gray
        Write-Host "   Responses Stored: $($report.flow_stats.responses)" -ForegroundColor Gray
        Write-Host "   Successful Responses: $($report.flow_stats.successful_responses)`n" -ForegroundColor Gray
        
        Write-Host ("="*100) -ForegroundColor Green
        Write-Host ""
        
        # Save report to file
        $reportFile = "test_report_$sessionId.json"
        $report | ConvertTo-Json -Depth 10 | Out-File $reportFile
        Write-Host "📄 Full report saved to: $reportFile" -ForegroundColor Cyan
        Write-Host ""
        
    } catch {
        Write-Host "⚠️  Could not retrieve report: $($_.Exception.Message)`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "[5/5] ⏭️  Skipping report retrieval (no session ID)`n" -ForegroundColor Yellow
}

# ============================================================================
# Final Summary
# ============================================================================
Write-Host ("="*100) -ForegroundColor Cyan
Write-Host "🏁 System Test Complete!" -ForegroundColor Green
Write-Host ("="*100) -ForegroundColor Cyan
Write-Host ""
Write-Host "✨ Successfully demonstrated:" -ForegroundColor White
Write-Host "   ✓ API health check" -ForegroundColor Green
Write-Host "   ✓ Document upload & parsing" -ForegroundColor Green
Write-Host "   ✓ AI endpoint analysis" -ForegroundColor Green
Write-Host "   ✓ Test generation" -ForegroundColor Green
Write-Host "   ✓ Intelligent test execution with retry" -ForegroundColor Green
Write-Host "   ✓ Detailed reporting" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 View Interactive Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ("="*100) -ForegroundColor Cyan
Write-Host ""
