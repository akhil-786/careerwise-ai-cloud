$ErrorActionPreference = "Stop"

# ============================================================
# CareerCloud AI - LocalStack Recovery
# ============================================================

$Project = "D:\Projects\CareerCloud-AI"

$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = "us-east-1"

$env:DYNAMODB_ENDPOINT = "http://localhost:4566"

Set-Location $Project

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "      CareerCloud AI - LocalStack Recovery" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# Check Gemini key
# ------------------------------------------------------------

if ($env:GEMINI_API_KEY) {
    Write-Host "Gemini API key: available" -ForegroundColor Green
}
else {
    Write-Host "Gemini API key: NOT SET" -ForegroundColor Yellow
    Write-Host "Recommendation/Roadmap AI calls may not work." -ForegroundColor Yellow
}

# ------------------------------------------------------------
# Check LocalStack container
# ------------------------------------------------------------

Write-Host ""
Write-Host "Checking LocalStack..." -ForegroundColor Cyan

$running = docker inspect -f "{{.State.Running}}" localstack 2>$null

if ($running -ne "true") {

    Write-Host "LocalStack is stopped. Starting it..." -ForegroundColor Yellow

    docker start localstack | Out-Null

    Write-Host "Waiting for LocalStack..." -ForegroundColor Yellow

    Start-Sleep -Seconds 8
}

Write-Host "LocalStack container is running." -ForegroundColor Green

# ------------------------------------------------------------
# Health check
# ------------------------------------------------------------

try {

    $health = Invoke-RestMethod `
        -Uri "http://localhost:4566/_localstack/health" `
        -Method Get

    Write-Host "LocalStack health: OK" -ForegroundColor Green

}
catch {

    Write-Host ""
    Write-Host "LocalStack health check failed." -ForegroundColor Red
    Write-Host "Stopping recovery process." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------
# Verify persistent DynamoDB tables
# IMPORTANT:
# We DO NOT create/delete/recreate tables here.
# ------------------------------------------------------------

Write-Host ""
Write-Host "Checking existing DynamoDB tables..." -ForegroundColor Cyan

python -c "import boto3; d=boto3.client('dynamodb',endpoint_url='http://localhost:4566',region_name='us-east-1'); print('Tables:', d.list_tables()['TableNames'])"

if ($LASTEXITCODE -ne 0) {

    Write-Host "Could not access DynamoDB." -ForegroundColor Red
    exit 1
}

Write-Host "DynamoDB check completed." -ForegroundColor Green

# ------------------------------------------------------------
# Run boto3 infrastructure recovery
# ------------------------------------------------------------

Write-Host ""
Write-Host "Starting Lambda/API Gateway recovery..." -ForegroundColor Cyan
Write-Host ""

python ".\infrastructure\setup-localstack.py"

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host " Recovery FAILED" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    exit $LASTEXITCODE
}

# ------------------------------------------------------------
# Verify Lambda functions
# ------------------------------------------------------------

Write-Host ""
Write-Host "Verifying Lambda functions..." -ForegroundColor Cyan

python -c "import boto3; l=boto3.client('lambda',endpoint_url='http://localhost:4566',region_name='us-east-1'); fs=l.list_functions()['Functions']; names=[f['FunctionName'] for f in fs if f['FunctionName'].startswith('CareerCloud')]; print('Lambdas:', names)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Lambda verification failed." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------
# Verify API Gateway
# ------------------------------------------------------------

Write-Host ""
Write-Host "Verifying API Gateway..." -ForegroundColor Cyan

python -c "import boto3; a=boto3.client('apigateway',endpoint_url='http://localhost:4566',region_name='us-east-1'); apis=a.get_rest_apis()['items']; x=[p for p in apis if p['name']=='CareerCloudAPI']; print('CareerCloudAPI:', [(p['id'],p['name']) for p in x])"

if ($LASTEXITCODE -ne 0) {
    Write-Host "API Gateway verification failed." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "       CareerCloud Recovery Completed" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""

Write-Host "LocalStack:              OK" -ForegroundColor Green
Write-Host "DynamoDB:                Preserved" -ForegroundColor Green
Write-Host "Lambda functions:        Restored/verified" -ForegroundColor Green
Write-Host "API Gateway:             Restored/verified" -ForegroundColor Green
Write-Host "Dev stage:               Restored by recovery script" -ForegroundColor Green
Write-Host "n8n:                     Untouched" -ForegroundColor Green
Write-Host "MongoDB:                 Untouched" -ForegroundColor Green

Write-Host ""
Write-Host "IMPORTANT: DynamoDB tables/data were NOT deleted or recreated." -ForegroundColor Cyan
Write-Host ""
