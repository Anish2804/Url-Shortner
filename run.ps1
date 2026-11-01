# PowerShell developer automation script for URL Shortening & Distributed Analytics Platform
param (
    [Parameter(Position=0)]
    [ValidateSet("dev", "worker", "rollup", "test", "coverage", "lint", "benchmark", "lock", "help")]
    [string]$Command = "help"
)

$VenvPython = ".venv\Scripts\python.exe"
$VenvPytest = ".venv\Scripts\pytest.exe"
$VenvUvicorn = ".venv\Scripts\uvicorn.exe"
$VenvFlake8 = ".venv\Scripts\flake8.exe"

switch ($Command) {
    "dev" {
        Write-Host "Starting LinkScale FastAPI Dev Server on http://localhost:8000..." -ForegroundColor Cyan
        & $VenvUvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    }
    "worker" {
        Write-Host "Starting LinkScale Kafka Analytics Worker..." -ForegroundColor Cyan
        & $VenvPython -m app.workers.analytics_worker
    }
    "rollup" {
        Write-Host "Triggering Daily Analytics Rollup Cron Job..." -ForegroundColor Cyan
        & $VenvPython -m app.workers.aggregation_cron
    }
    "test" {
        Write-Host "Executing full test suite..." -ForegroundColor Green
        & $VenvPytest -v tests/
    }
    "coverage" {
        Write-Host "Executing test suite with branch coverage report..." -ForegroundColor Green
        & $VenvPytest --cov=app --cov-report=term-missing --cov-report=html tests/
    }
    "lint" {
        Write-Host "Running flake8 code quality audit..." -ForegroundColor Magenta
        & $VenvFlake8 app --max-line-length=120
    }
    "benchmark" {
        Write-Host "Running performance benchmark against http://localhost:8000..." -ForegroundColor Yellow
        & $VenvPython tests/performance/benchmark_runner.py --url http://localhost:8000 -c 20 -n 1000 --paths /health /metrics
    }
    "lock" {
        Write-Host "Freezing exact virtual environment dependencies to requirements.lock..." -ForegroundColor Yellow
        & $VenvPython -m pip freeze > requirements.lock
        Write-Host "Saved requirements.lock" -ForegroundColor Green
    }
    default {
        Write-Host "LinkScale Developer Automation CLI" -ForegroundColor White
        Write-Host "Usage: .\run.ps1 [command]"
        Write-Host "  dev        - Start FastAPI server with live reload"
        Write-Host "  worker     - Run Kafka analytics consumer worker"
        Write-Host "  rollup     - Run daily analytics aggregation cron"
        Write-Host "  test       - Run all unit and integration tests"
        Write-Host "  coverage   - Run tests with full coverage report"
        Write-Host "  lint       - Run flake8 code quality checks"
        Write-Host "  benchmark  - Execute latency & RPS benchmark runner"
        Write-Host "  lock       - Generate frozen requirements.lock"
    }
}
