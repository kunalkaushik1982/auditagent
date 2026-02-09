# Start Celery Worker for Audit Agent (Parallel Processing)
# 
# This script starts a Celery worker with thread pool to process 
# multiple audit tasks in parallel.

Write-Host "Starting Celery Worker with Thread Pool for Parallel Processing..." -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This worker can process multiple audits simultaneously!" -ForegroundColor Green
Write-Host "Keep this terminal running while using the application." -ForegroundColor Yellow
Write-Host ""

# Start Celery with thread pool (allows parallel processing)
# Windows doesn't support prefork pool, so we use threads
# Concurrency=4 means up to 4 audits can run simultaneously
celery -A backend.app.celery_app worker --loglevel=info --pool=threads --concurrency=4

Write-Host ""
Write-Host "Celery worker stopped." -ForegroundColor Red
