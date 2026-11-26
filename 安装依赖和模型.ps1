$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = 'python'
& $python -c "import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12), 'Requires Python 3.10–3.12'"
if ($LASTEXITCODE -ne 0) { throw 'Requires Python 3.10–3.12.' }
& $python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$modelPath = Join-Path $PSScriptRoot 'models\vosk-model-small-cn-0.22\am\final.mdl'
if (!(Test-Path -LiteralPath $modelPath)) {
    $archive = Join-Path $PSScriptRoot 'models\vosk-model-small-cn-0.22.zip'
    New-Item -ItemType Directory -Force (Split-Path -Parent $archive) | Out-Null
    Invoke-WebRequest -Uri 'https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip' -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath (Split-Path -Parent $archive) -Force
}
Write-Host 'Ready. Double-click the app EXE for a console-free start.'
