# 穿搭 Agent 合并版 — 一键启动
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"

# 检查 venv
if (-not (Test-Path $python)) {
    Write-Host "[!] 未找到 backend\.venv，请先创建：" -ForegroundColor Yellow
    Write-Host "    cd backend && uv venv .venv --python 3.12 && uv pip install -r requirements.txt --python .venv\Scripts\python.exe"
    pause; exit 1
}

# 检查 .env
if (-not (Test-Path (Join-Path $backendDir ".env"))) {
    Write-Host "[!] 未找到 backend\.env，请复制 .env.example 并填入 API Key" -ForegroundColor Yellow
    pause; exit 1
}

Write-Host "=== 穿搭 Agent ===" -ForegroundColor Cyan
Write-Host "后端: http://127.0.0.1:8080"
Write-Host "前端: http://127.0.0.1:3030"
Write-Host ""

# 启动后端
$backendProc = Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8080" -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru

# 启动前端
$frontendProc = Start-Process -FilePath $python -ArgumentList "-m", "http.server", "3030" -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru

Write-Host "[OK] 已启动，按任意键停止..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 清理
Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
Write-Host "已停止。"
