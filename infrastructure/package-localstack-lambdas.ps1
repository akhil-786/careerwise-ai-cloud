param(
    [string[]]$FunctionNames = @("auth", "users", "assessment", "recommendation", "roadmap", "resume-screening")
)

$ErrorActionPreference = "Stop"

$functionsRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\backend\functions")).Path

foreach ($name in $FunctionNames) {
    $functionDir = Join-Path $functionsRoot $name
    $requirements = Join-Path $functionDir "requirements.txt"
    $handler = Join-Path $functionDir "handler.py"
    $buildDir = Join-Path $functionDir ".localstack-build"
    $packageDir = Join-Path $buildDir "package"
    $zipPath = Join-Path $functionDir "$name-lambda-localstack.zip"

    if (!(Test-Path -LiteralPath $handler) -or !(Test-Path -LiteralPath $requirements)) {
        throw "Missing handler.py or requirements.txt for $name"
    }

    if (Test-Path -LiteralPath $buildDir) {
        Remove-Item -LiteralPath $buildDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $packageDir | Out-Null
    Copy-Item -LiteralPath $requirements -Destination (Join-Path $buildDir "requirements.txt")

    Write-Host "Installing Linux Python 3.12 dependencies for $name..."
    docker run --rm --entrypoint /bin/sh `
        --mount "type=bind,source=$buildDir,target=/build" `
        public.ecr.aws/lambda/python:3.12 `
        -c "python -m pip install --no-cache-dir -r /build/requirements.txt -t /build/package"
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency packaging failed for $name. Ensure Docker Desktop is running Linux containers."
    }

    Copy-Item -LiteralPath $handler -Destination (Join-Path $packageDir "handler.py") -Force
    Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -CompressionLevel Fastest -Force
    Remove-Item -LiteralPath $buildDir -Recurse -Force
    Write-Host "Created $zipPath"
}
