# ====================================
# Echo UGC — 一键体检（测试方式改进件，2026-09-24 立）
# 用途：波次末/开工前跑一次；输出三命令结果 + 覆盖率 + 死码嫌疑人 + 中文摘要卡
# 快照：.sisyphus/evidence/baseline-latest.txt（PROJECT_STATE 数字以此为源，禁止手抄）
# ====================================
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Echo UGC 一键体检  $stamp" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$report = @()
$report += "Echo UGC 基线快照 $stamp"

# ---- 1/3 后端 pytest（含覆盖率门禁） ----
Write-Host "`n[1/3] 后端 pytest 全量..." -ForegroundColor Yellow
Push-Location "$root\backend"
$pyOut = & ".\.venv\Scripts\python.exe" -m pytest -q --no-header 2>&1
$pyExit = $LASTEXITCODE
Pop-Location
$pyText = $pyOut | Out-String
$passed = if ($pyText -match '(\d+) passed') { $Matches[1] } else { '?' }
$failed = if ($pyText -match '(\d+) failed') { $Matches[1] } else { '0' }
$cov = if ($pyText -match 'TOTAL\s+[\d\s,]+?(\d+)%') { $Matches[1] } else { '?' }
$deadMods = @($pyOut | Where-Object { $_ -is [string] -and $_ -match '^(app\S+\.py)\s+.*\s0%$' } | ForEach-Object { ($_ -split '\s+')[0] })
$gate = if ($pyExit -eq 0) { '通过' } else { '未过' }
Write-Host "  测试: $passed passed / $failed failed ｜ 覆盖率: $cov% ｜ 门禁: $gate" -ForegroundColor $(if ($pyExit -eq 0) { 'Green' } else { 'Red' })
if ($pyExit -ne 0) { Write-Host "  --- pytest 末尾输出（诊断用）---"; $pyOut | Select-Object -Last 8 | ForEach-Object { Write-Host "  $_" } }
$report += "后端: $passed passed / $failed failed, 覆盖率 $cov%, 门禁 $gate (exit $pyExit)"
if ($deadMods.Count -gt 0) { $report += "死码嫌疑人(0%模块): $($deadMods -join ', ')" } else { $report += "死码嫌疑人(0%模块): 无" }

# ---- 2/3 前端 tsc ----
Write-Host "`n[2/3] 前端 tsc 类型检查..." -ForegroundColor Yellow
Push-Location "$root\frontend"
npx tsc --noEmit 2>&1 | Out-Null
$tscExit = $LASTEXITCODE
Write-Host "  tsc: $(if ($tscExit -eq 0) { '0 错误' } else { '有错误' })" -ForegroundColor $(if ($tscExit -eq 0) { 'Green' } else { 'Red' })
$report += "前端 tsc: $(if ($tscExit -eq 0) { '0 错误' } else { "exit $tscExit" })"

# ---- 3/3 前端 vitest ----
Write-Host "`n[3/3] 前端 vitest..." -ForegroundColor Yellow
$vOut = npx vitest run 2>&1 | Out-String
$vExit = $LASTEXITCODE
$vPassed = if ($vOut -match 'Tests\s+(\d+) passed') { $Matches[1] } else { '?' }
Write-Host "  vitest: $vPassed passed (exit $vExit)" -ForegroundColor $(if ($vExit -eq 0) { 'Green' } else { 'Red' })
$report += "前端 vitest: $vPassed passed (exit $vExit)"
Pop-Location

# ---- 摘要卡 ----
$allGreen = ($pyExit -eq 0 -and $tscExit -eq 0 -and $vExit -eq 0)
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " 摘要：$(if ($allGreen) { '✅ 三命令全绿 —— 净基线成立' } else { '❌ 存在红项 —— 见上方明细' })" -ForegroundColor $(if ($allGreen) { 'Green' } else { 'Red' })
Write-Host " 死码嫌疑人: $(if ($deadMods.Count -gt 0) { $deadMods -join ', ' } else { '无' })"
Write-Host "========================================" -ForegroundColor Cyan

# ---- 快照落盘（gitignored 证据区） ----
$snapDir = "$root\.sisyphus\evidence"
New-Item -ItemType Directory -Path $snapDir -Force | Out-Null
$report | Set-Content -LiteralPath "$snapDir\baseline-latest.txt" -Encoding UTF8
Write-Host "`n快照已写: .sisyphus/evidence/baseline-latest.txt（PROJECT_STATE 数字以此为源）"
exit $(if ($allGreen) { 0 } else { 1 })
