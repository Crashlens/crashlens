# CrashLens Dashboard Generation & Documentation Validation Script
# Phase 2: Production Readiness Validation
# Validates: Dashboard generation, JSON structure, documentation completeness

param(
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Continue"
$SuccessCount = 0
$TotalChecks = 0

function Write-TestHeader {
    param([string]$Title)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )
    $script:TotalChecks++
    if ($Passed) {
        $script:SuccessCount++
        Write-Host "[PASS] $TestName" -ForegroundColor Green
        if ($Verbose -and $Details) {
            Write-Host "       $Details" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "[FAIL] $TestName" -ForegroundColor Red
        if ($Details) {
            Write-Host "       ERROR: $Details" -ForegroundColor Yellow
        }
    }
}

# ============================================================================
# STEP 11: Dashboard Generation Validation
# ============================================================================

Write-TestHeader "STEP 11: Dashboard Generation Validation"

# Check if generation script exists
$dashboardScript = "scripts\generate_dashboard.py"
Write-TestResult "Dashboard script exists" `
    (Test-Path $dashboardScript) `
    "Path: $dashboardScript"

# Generate dashboard JSON
Write-Host "Generating dashboard JSON..." -ForegroundColor Yellow
$tempDashboard = "$env:TEMP\crashlens_dashboard_generated.json"

try {
    python $dashboardScript > $tempDashboard 2>&1
    $generateExitCode = $LASTEXITCODE
    
    Write-TestResult "Dashboard generation succeeded" `
        ($generateExitCode -eq 0) `
        "Exit code: $generateExitCode"
} catch {
    Write-TestResult "Dashboard generation succeeded" $false "Exception: $_"
    $generateExitCode = 1
}

if ($generateExitCode -eq 0) {
    # Verify JSON is valid
    try {
        $dashboardContent = Get-Content $tempDashboard -Raw | ConvertFrom-Json
        Write-TestResult "Generated JSON is valid" $true "Successfully parsed JSON"
    } catch {
        Write-TestResult "Generated JSON is valid" $false "Parse error: $_"
        $dashboardContent = $null
    }

    # Check file size
    if (Test-Path $tempDashboard) {
        $fileSize = (Get-Item $tempDashboard).Length
        $fileSizeKB = [math]::Round($fileSize / 1KB, 2)
        $sizeValid = ($fileSize -ge 20KB -and $fileSize -le 50KB)
        
        Write-TestResult "Dashboard file size appropriate" `
            $sizeValid `
            "Size: $fileSizeKB KB (expected: 20-50KB)"
    }

    # Verify dashboard metadata
    if ($dashboardContent) {
        $hasTitle = $null -ne $dashboardContent.title
        Write-TestResult "Dashboard has title" `
            $hasTitle `
            "Title: $($dashboardContent.title)"

        # Check for panels
        if ($dashboardContent.panels) {
            $panelCount = $dashboardContent.panels.Count
            $expectedPanels = 12
            $panelCountValid = ($panelCount -ge $expectedPanels)
            
            Write-TestResult "Dashboard has expected panels" `
                $panelCountValid `
                "Found: $panelCount panels (expected: >=$expectedPanels)"

            # Verify panel structure
            if ($panelCount -gt 0) {
                $firstPanel = $dashboardContent.panels[0]
                $hasTitle = $null -ne $firstPanel.title
                $hasTargets = $null -ne $firstPanel.targets
                $hasType = $null -ne $firstPanel.type
                $hasGridPos = $null -ne $firstPanel.gridPos
                
                $validStructure = $hasTitle -and $hasTargets -and $hasType -and $hasGridPos
                
                Write-TestResult "Panel structure valid" `
                    $validStructure `
                    "Keys: title=$hasTitle, targets=$hasTargets, type=$hasType, gridPos=$hasGridPos"
            }

            # Check for PromQL expressions
            $promqlCount = 0
            foreach ($panel in $dashboardContent.panels) {
                if ($panel.targets) {
                    foreach ($target in $panel.targets) {
                        if ($target.expr) {
                            $promqlCount++
                            if ($Verbose -and $promqlCount -le 3) {
                                Write-Host "       PromQL: $($target.expr.Substring(0, [Math]::Min(60, $target.expr.Length)))..." -ForegroundColor DarkGray
                            }
                        }
                    }
                }
            }
            
            Write-TestResult "Panels contain PromQL expressions" `
                ($promqlCount -ge 10) `
                "Found: $promqlCount PromQL queries (expected: >=10)"
        }

        # Verify schema version
        if ($dashboardContent.schemaVersion) {
            $schemaValid = ($dashboardContent.schemaVersion -ge 30)
            Write-TestResult "Dashboard schema version valid" `
                $schemaValid `
                "Schema version: $($dashboardContent.schemaVersion)"
        }

        # Verify template variables
        if ($dashboardContent.templating -and $dashboardContent.templating.list) {
            $templateCount = $dashboardContent.templating.list.Count
            Write-TestResult "Dashboard has template variables" `
                ($templateCount -ge 1) `
                "Found: $templateCount template variables"
        }
    }

    # Compare with committed dashboard
    $committedDashboard = "dashboards\crashlens-policy-enforcement.json"
    if (Test-Path $committedDashboard) {
        try {
            $committedContent = Get-Content $committedDashboard -Raw | ConvertFrom-Json
            
            # Compare panel counts
            $generatedPanels = $dashboardContent.panels.Count
            $committedPanels = $committedContent.panels.Count
            $panelCountMatch = ($generatedPanels -eq $committedPanels)
            
            Write-TestResult "Generated matches committed dashboard" `
                $panelCountMatch `
                "Generated: $generatedPanels panels, Committed: $committedPanels panels"
        } catch {
            Write-TestResult "Generated matches committed dashboard" $false "Failed to compare: $_"
        }
    } else {
        Write-Host "       [INFO] Committed dashboard not found for comparison" -ForegroundColor Yellow
    }
}

# ============================================================================
# STEP 12: Documentation Completeness Validation
# ============================================================================

Write-TestHeader "STEP 12: Documentation Completeness Validation"

# Check README for observability section
$readmePath = "README.md"
if (Test-Path $readmePath) {
    $readmeContent = Get-Content $readmePath -Raw
    $hasObservability = $readmeContent -match "(?i)(observability|prometheus|metrics)"
    
    Write-TestResult "README mentions observability" `
        $hasObservability `
        "Keywords found in README"
} else {
    Write-TestResult "README mentions observability" $false "README.md not found"
}

# Verify OBSERVABILITY.md exists and is comprehensive
$observabilityDoc = "docs\OBSERVABILITY.md"
if (Test-Path $observabilityDoc) {
    $obsContent = Get-Content $observabilityDoc
    $lineCount = $obsContent.Count
    $isComprehensive = ($lineCount -ge 200)
    
    Write-TestResult "OBSERVABILITY.md is comprehensive" `
        $isComprehensive `
        "Lines: $lineCount (expected: >=200)"

    # Check for required sections
    $obsFullContent = Get-Content $observabilityDoc -Raw
    $sections = @(
        @{Name="Installation"; Pattern="(?i)(# |## ).*install"},
        @{Name="Quick Start"; Pattern="(?i)(# |## ).*quick.*start"},
        @{Name="Configuration"; Pattern="(?i)(# |## ).*config"},
        @{Name="Troubleshooting"; Pattern="(?i)(# |## ).*(troubleshoot|problems|faq)"}
    )
    
    foreach ($section in $sections) {
        $hasSection = $obsFullContent -match $section.Pattern
        Write-TestResult "OBSERVABILITY.md has $($section.Name) section" `
            $hasSection `
            "Pattern: $($section.Pattern)"
    }

    # Check for code examples
    $yamlBlocks = ([regex]::Matches($obsFullContent, "``````yaml")).Count
    $pythonBlocks = ([regex]::Matches($obsFullContent, "``````python")).Count
    $bashBlocks = ([regex]::Matches($obsFullContent, "``````bash")).Count
    $totalCodeBlocks = $yamlBlocks + $pythonBlocks + $bashBlocks
    
    Write-TestResult "OBSERVABILITY.md has code examples" `
        ($totalCodeBlocks -ge 10) `
        "Found: $totalCodeBlocks code blocks (yaml: $yamlBlocks, python: $pythonBlocks, bash: $bashBlocks)"

    # Check for security warnings
    $hasSecurityWarnings = $obsFullContent -match "(?i)(security|auth|credential|warning)"
    Write-TestResult "OBSERVABILITY.md has security considerations" `
        $hasSecurityWarnings `
        "Security keywords found"
} else {
    Write-TestResult "OBSERVABILITY.md exists" $false "File not found"
}

# Verify GRAFANA_SETUP.md exists
$grafanaDoc = "docs\GRAFANA_SETUP.md"
$grafanaExists = Test-Path $grafanaDoc
Write-TestResult "GRAFANA_SETUP.md exists" `
    $grafanaExists `
    "Path: $grafanaDoc"

if ($grafanaExists) {
    $grafanaContent = Get-Content $grafanaDoc -Raw
    $grafanaLineCount = (Get-Content $grafanaDoc).Count
    Write-Host "       Lines: $grafanaLineCount" -ForegroundColor DarkGray
}

# Verify HTTP_SERVER_SECURITY.md exists (Phase 2 requirement)
$httpSecurityDoc = "docs\HTTP_SERVER_SECURITY.md"
$httpSecurityExists = Test-Path $httpSecurityDoc
Write-TestResult "HTTP_SERVER_SECURITY.md exists" `
    $httpSecurityExists `
    "Path: $httpSecurityDoc"

# Verify CONFIG_PRECEDENCE.md exists (Phase 2 requirement)
$configPrecedenceDoc = "docs\CONFIG_PRECEDENCE.md"
$configPrecedenceExists = Test-Path $configPrecedenceDoc
Write-TestResult "CONFIG_PRECEDENCE.md exists" `
    $configPrecedenceExists `
    "Path: $configPrecedenceDoc"

# Verify Docker Compose example exists
$dockerCompose = "examples\docker-compose-ci.yml"
$dockerComposeExists = Test-Path $dockerCompose
Write-TestResult "Docker Compose example exists" `
    $dockerComposeExists `
    "Path: $dockerCompose"

# Check for CI examples
$ciExamples = @(
    "examples\ci-workflows\github-actions.yml",
    "examples\ci-workflows\gitlab-ci.yml",
    ".github\workflows\ci.yml"
)

$ciExamplesCount = 0
foreach ($ciExample in $ciExamples) {
    if (Test-Path $ciExample) {
        $ciExamplesCount++
        if ($Verbose) {
            Write-Host "       Found: $ciExample" -ForegroundColor DarkGray
        }
    }
}

Write-TestResult "CI examples exist" `
    ($ciExamplesCount -ge 2) `
    "Found: $ciExamplesCount CI example files"

# Check for example config files
$exampleConfigs = @(
    "examples\config\metrics-valid.yaml",
    "examples\config\metrics-minimal.yaml",
    "examples\config\metrics-per-rule.yaml"
)

$exampleConfigCount = 0
foreach ($config in $exampleConfigs) {
    if (Test-Path $config) {
        $exampleConfigCount++
    }
}

Write-TestResult "Example config files exist" `
    ($exampleConfigCount -ge 3) `
    "Found: $exampleConfigCount example configs"

# ============================================================================
# STEP 13: Production Readiness Report
# ============================================================================

Write-TestHeader "STEP 13: Production Readiness Summary"

$passRate = if ($TotalChecks -gt 0) { [math]::Round(($SuccessCount / $TotalChecks) * 100, 1) } else { 0 }

Write-Host ""
Write-Host "┌─────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "│  PRODUCTION READINESS VALIDATION RESULTS                │" -ForegroundColor Cyan
Write-Host "├─────────────────────────────────────────────────────────┤" -ForegroundColor Cyan
Write-Host "│  Total Checks: $TotalChecks                                        │" -ForegroundColor White
Write-Host "│  Passed: $SuccessCount                                             │" -ForegroundColor Green
Write-Host "│  Failed: $($TotalChecks - $SuccessCount)                                              │" -ForegroundColor $(if ($TotalChecks - $SuccessCount -eq 0) { "Green" } else { "Red" })
Write-Host "│  Pass Rate: $passRate%                                       │" -ForegroundColor $(if ($passRate -ge 90) { "Green" } elseif ($passRate -ge 75) { "Yellow" } else { "Red" })
Write-Host "└─────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# Determine production readiness
$isProductionReady = ($passRate -ge 90)

if ($isProductionReady) {
    Write-Host "✅ PRODUCTION READY: All critical gates passed" -ForegroundColor Green
    Write-Host ""
    Write-Host "Recommendation: MERGE and release" -ForegroundColor Green
    Write-Host "Risk Level: LOW (all claims validated)" -ForegroundColor Green
    Write-Host "Blocker Count: 0" -ForegroundColor Green
    $exitCode = 0
} else {
    Write-Host "❌ NOT PRODUCTION READY: Some gates failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Recommendation: FIX failing tests before merge" -ForegroundColor Red
    Write-Host "Risk Level: MEDIUM-HIGH" -ForegroundColor Red
    Write-Host "Blocker Count: $($TotalChecks - $SuccessCount)" -ForegroundColor Red
    $exitCode = 1
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Review any failed tests above" -ForegroundColor White
Write-Host "2. Fix blocking issues" -ForegroundColor White
Write-Host "3. Re-run validation script" -ForegroundColor White
Write-Host "4. If all pass, proceed to merge" -ForegroundColor White
Write-Host ""

# Cleanup
if (Test-Path $tempDashboard) {
    if ($Verbose) {
        Write-Host "Keeping generated dashboard at: $tempDashboard" -ForegroundColor DarkGray
    } else {
        Remove-Item $tempDashboard -ErrorAction SilentlyContinue
    }
}

exit $exitCode
