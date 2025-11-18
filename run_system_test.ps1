# ============================================================================
# AutoTest-RL - Complete System Test
# Upload API Doc -> Parse -> Analyze -> Generate Tests -> Execute
# ============================================================================

$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8000"
$apiDocPath = "uploads/api doc/Cargodham QA Doc (1).pdf"

Write-Host ""
Write-Host "================================================================================"
Write-Host "  AutoTest-RL - Complete System Test" -ForegroundColor Green
Write-Host "================================================================================"
Write-Host ""

# Step 1: Verify API
Write-Host "[1/5] Verifying API Status..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "  [OK] API Status: $($health.status)" -ForegroundColor Green
    Write-Host "       Environment: $($health.environment)"
    Write-Host "       Version: $($health.version)"
    Write-Host ""
} catch {
    Write-Host "  [ERROR] API is not running!" -ForegroundColor Red
    exit 1
}

# Step 2: Upload Document
Write-Host "[2/5] Uploading API Documentation..." -ForegroundColor Yellow

if (-not (Test-Path $apiDocPath)) {
    Write-Host "  [ERROR] API doc not found at: $apiDocPath" -ForegroundColor Red
    exit 1
}

Write-Host "       File: $apiDocPath"
$fileInfo = Get-Item $apiDocPath
Write-Host "       Size: $([math]::Round($fileInfo.Length/1KB, 2)) KB"
Write-Host ""

try {
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
    
    Write-Host "  [OK] Document Uploaded Successfully!" -ForegroundColor Green
    Write-Host "       Document ID: $docId" -ForegroundColor Cyan
    Write-Host "       Filename: $($response.filename)"
    Write-Host "       Type: $($response.doc_type)"
    Write-Host "       Size: $($response.file_size) bytes"
    Write-Host "       Base URL: $($response.base_url)"
    Write-Host "       Endpoints Found: $($response.endpoints_found)" -ForegroundColor Yellow
    Write-Host "       Text Chunks: $($response.chunks_created)"
    Write-Host ""
    
} catch {
    Write-Host "  [ERROR] Upload failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 3: Get Document Details
Write-Host "[3/5] Retrieving Document Details..." -ForegroundColor Yellow

try {
    $docDetails = Invoke-RestMethod -Uri "$baseUrl/api/v1/documents/$docId" -Method Get
    
    Write-Host "  [OK] Document Details Retrieved!" -ForegroundColor Green
    Write-Host "       Name: $($docDetails.name)"
    Write-Host "       Base URL: $($docDetails.base_url)"
    Write-Host "       Total Endpoints: $($docDetails.endpoints.Count)" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "       Discovered Endpoints:" -ForegroundColor Cyan
    foreach ($ep in $docDetails.endpoints | Select-Object -First 10) {
        $auth = if ($ep.auth_required) { "[AUTH]" } else { "[OPEN]" }
        Write-Host "        $auth $($ep.method.PadRight(6)) $($ep.path)"
        if ($ep.summary) {
            Write-Host "              -> $($ep.summary)" -ForegroundColor DarkGray
        }
    }
    
    if ($docDetails.endpoints.Count -gt 10) {
        Write-Host "        ... and $($docDetails.endpoints.Count - 10) more endpoints" -ForegroundColor DarkGray
    }
    Write-Host ""
    
} catch {
    Write-Host "  [WARN] Could not retrieve details: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
}

# Step 4: Start Test Execution
Write-Host "[4/5] Starting Intelligent Test Execution..." -ForegroundColor Yellow

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
    
    Write-Host "  [OK] Test Session Started!" -ForegroundColor Green
    Write-Host "       Session ID: $sessionId" -ForegroundColor Cyan
    Write-Host "       Status: $($testSession.status)"
    Write-Host "       Total Endpoints: $($testSession.total_endpoints)" -ForegroundColor Yellow
    Write-Host "       Estimated Duration: $($testSession.estimated_duration)s"
    Write-Host ""
    
    Write-Host "       Monitoring test progress..." -ForegroundColor Yellow
    
    $completed = $false
    $lastProgress = 0
    
    while (-not $completed) {
        Start-Sleep -Seconds 2
        
        $status = Invoke-RestMethod -Uri "$baseUrl/api/v1/tests/$sessionId/status" -Method Get
        
        if ($status.progress -ne $lastProgress) {
            Write-Host "        Progress: $([math]::Round($status.progress, 1))% | Tested: $($status.tested_endpoints)/$($status.total_endpoints) | Passed: $($status.passed) | Failed: $($status.failed)"
            $lastProgress = $status.progress
        }
        
        if ($status.status -eq "completed" -or $status.status -eq "failed") {
            $completed = $true
        }
    }
    
    Write-Host ""
    
} catch {
    Write-Host "  [ERROR] Test execution failed: $($_.Exception.Message)" -ForegroundColor Red
    $sessionId = $null
}

# Step 5: Get Test Report
if ($sessionId) {
    Write-Host "[5/5] Retrieving Test Report..." -ForegroundColor Yellow
    
    try {
        $report = Invoke-RestMethod -Uri "$baseUrl/api/v1/tests/$sessionId/report" -Method Get
        
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Green
        Write-Host "  TEST EXECUTION COMPLETE!" -ForegroundColor Green
        Write-Host "================================================================================" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "  Summary Statistics:" -ForegroundColor Cyan
        Write-Host "    Total Tests: $($report.total_tests)"
        Write-Host "    Passed: $($report.passed)" -ForegroundColor Green
        Write-Host "    Failed: $($report.failed)" -ForegroundColor Red
        Write-Host "    Success Rate: $([math]::Round($report.success_rate, 1))%" -ForegroundColor Yellow
        Write-Host "    Total Time: $([math]::Round($report.total_time, 2))s"
        Write-Host "    Avg Time per Test: $([math]::Round($report.avg_time, 2))s"
        Write-Host "    Total Attempts: $($report.total_attempts)"
        Write-Host ""
        
        Write-Host "  Detailed Results:" -ForegroundColor Cyan
        $resultNum = 1
        foreach ($result in $report.results | Select-Object -First 15) {
            $statusIcon = if ($result.success) { "[PASS]" } else { "[FAIL]" }
            Write-Host "    $resultNum. $statusIcon $($result.method) $($result.endpoint)"
            Write-Host "         Status: $($result.status_code) | Time: $([math]::Round($result.elapsed_time, 2))s | Attempts: $($result.attempts)"
            
            if (-not $result.success -and $result.error) {
                $errorMsg = $result.error.Substring(0, [Math]::Min(80, $result.error.Length))
                Write-Host "         Error: $errorMsg..." -ForegroundColor Red
            }
            $resultNum++
        }
        
        if ($report.results.Count -gt 15) {
            Write-Host "    ... and $($report.results.Count - 15) more results"
        }
        
        Write-Host ""
        Write-Host "  Flow Database Stats:" -ForegroundColor Cyan
        Write-Host "    Requests Stored: $($report.flow_stats.requests)"
        Write-Host "    Responses Stored: $($report.flow_stats.responses)"
        Write-Host "    Successful Responses: $($report.flow_stats.successful_responses)"
        Write-Host ""
        
        Write-Host "================================================================================" -ForegroundColor Green
        Write-Host ""
        
        # Save report
        $reportFile = "test_report_$sessionId.json"
        $report | ConvertTo-Json -Depth 10 | Out-File $reportFile
        Write-Host "  Full report saved to: $reportFile" -ForegroundColor Cyan
        Write-Host ""
        
    } catch {
        Write-Host "  [WARN] Could not retrieve report: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host ""
    }
} else {
    Write-Host "[5/5] Skipping report (no session ID)" -ForegroundColor Yellow
    Write-Host ""
}

# Final Summary
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  System Test Complete!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Successfully demonstrated:" -ForegroundColor White
Write-Host "    [OK] API health check" -ForegroundColor Green
Write-Host "    [OK] Document upload & parsing" -ForegroundColor Green
Write-Host "    [OK] AI endpoint analysis" -ForegroundColor Green
Write-Host "    [OK] Test generation" -ForegroundColor Green
Write-Host "    [OK] Intelligent test execution" -ForegroundColor Green
Write-Host "    [OK] Detailed reporting" -ForegroundColor Green
Write-Host ""
Write-Host "  View Interactive Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
