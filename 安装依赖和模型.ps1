$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $venvPython)) {
    & python -c "import sys; sys.exit(not ((3, 9) <= sys.version_info[:2] <= (3, 12)))"
    if ($LASTEXITCODE -ne 0) { throw 'Requires Python 3.9–3.12.' }
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed. Close YapDash before retrying.' }
}
$pipOptions = @('--timeout', '120', '--retries', '5')
$wheelhouse = Join-Path $PSScriptRoot 'wheels39'
$pythonTarget = & $venvPython -c "import sys, struct; print('%d.%d-%d' % (*sys.version_info[:2], struct.calcsize('P') * 8))"
if ($LASTEXITCODE -ne 0) { throw 'Could not start the project Python.' }
if ($pythonTarget -eq '3.9-64' -and (Test-Path -LiteralPath $wheelhouse -PathType Container)) {
    $pipOptions = @('--no-index', '--find-links', $wheelhouse)
}
$bundledWheels = @()
$pinyinWheel = Join-Path $PSScriptRoot 'wheels\pypinyin-0.55.0-py2.py3-none-any.whl'
if (Test-Path -LiteralPath $pinyinWheel -PathType Leaf) {
    $bundledWheels += $pinyinWheel
}
& $venvPython -m pip install @pipOptions -r requirements.txt @bundledWheels
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.venv\Scripts\python.exe' .\launch.pyw --check-qt
if ($LASTEXITCODE -ne 0) { throw 'Qt startup check failed. Check that the PyQt5 installation is complete.' }
$modelName = 'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17'
$root = Join-Path $PSScriptRoot 'models'
$dir = Join-Path $root $modelName
$source = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models'
New-Item -ItemType Directory -Force $root | Out-Null
if (!(Test-Path (Join-Path $dir 'model.int8.onnx')) -or !(Test-Path (Join-Path $dir 'tokens.txt'))) {
    $archive = Join-Path $root ($modelName + '.tar.bz2')
    $url = "$source/$modelName.tar.bz2"
    $partial = "$archive.part"
    if (!(Test-Path -LiteralPath $archive) -or (Get-Item -LiteralPath $archive).Length -lt 100MB) {
        Write-Host 'Downloading the SenseVoice model. This may take several minutes.'
        curl.exe -fL --connect-timeout 15 --max-time 600 $url -o $partial
        if ($LASTEXITCODE -eq 0) {
            Move-Item -Force -LiteralPath $partial -Destination $archive
        } else {
            Write-Host 'GitHub download failed. Trying the Hugging Face mirror.'
            $mirror = 'https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main'
            New-Item -ItemType Directory -Force $dir | Out-Null
            $model = Join-Path $dir 'model.int8.onnx'
            $tokens = Join-Path $dir 'tokens.txt'
            curl.exe -fL --connect-timeout 15 --max-time 600 "$mirror/model.int8.onnx" -o "$model.part"
            if ($LASTEXITCODE -ne 0) { throw "Both model downloads failed. Download $url in your browser, save it in $root, then rerun this script." }
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath "$model.part").Hash
            if ($hash -ne 'c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51') { throw 'SenseVoice model checksum mismatch.' }
            curl.exe -fLsS --connect-timeout 15 --max-time 60 "$mirror/tokens.txt" -o "$tokens.part"
            if ($LASTEXITCODE -ne 0) { throw 'SenseVoice token download failed.' }
            Move-Item -Force -LiteralPath "$tokens.part" -Destination $tokens
            Move-Item -Force -LiteralPath "$model.part" -Destination $model
        }
    }
    if (!(Test-Path (Join-Path $dir 'model.int8.onnx')) -or !(Test-Path (Join-Path $dir 'tokens.txt'))) {
        tar.exe -xf $archive -C $root
        if ($LASTEXITCODE -ne 0) { throw 'SenseVoice extraction failed.' }
        Remove-Item -LiteralPath $archive
    }
}
$vad = Join-Path $dir 'silero_vad.onnx'
if (!(Test-Path $vad)) {
    curl.exe -fLsS --connect-timeout 15 --max-time 120 --retry 2 "$source/silero_vad.onnx" -o "$vad.part"
    if ($LASTEXITCODE -ne 0) { throw 'Speech detection model download failed.' }
    Move-Item -LiteralPath "$vad.part" -Destination $vad
}
Write-Host 'Ready. Double-click the app EXE.'
