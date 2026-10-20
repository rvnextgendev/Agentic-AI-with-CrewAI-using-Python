param([switch]$InstallDependencies)

$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $appPython = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
    $createdEnvironment = $false
    if (-not (Test-Path -LiteralPath $appPython)) {
        & py -3.11 -m venv venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11, then run this script again.' }
        $createdEnvironment = $true
    }
    & $appPython runtime_check.py
    if ($LASTEXITCODE -ne 0) {
        throw 'The existing venv uses a different Python version. Create a Python 3.11 environment before continuing.'
    }
    if ($InstallDependencies -or $createdEnvironment) {
        & $appPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    $env:PYTHONIOENCODING = 'utf-8'
    & $appPython -m streamlit run streamlit_app.py
} finally {
    Pop-Location
}
