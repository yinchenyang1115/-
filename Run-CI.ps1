$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# The runner checkout and every generated file must stay on F:.
if ([IO.Path]::GetPathRoot($PSScriptRoot) -ne 'F:\') {
    throw 'Configure the runner work directory on F: before running CI.'
}
if (-not $env:MALL_DB_PASSWORD) {
    throw 'Set the repository secret MALL_DB_PASSWORD.'
}

$localRuntime = 'F:\softwaretesting\mall-loaal\.runtime'
$env:TEMP = Join-Path $localRuntime 'tmp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $localRuntime 'cache\pip'
$env:JAVA_HOME = Join-Path $localRuntime 'tools\jdk-17.0.20.1+1'
$env:JAVA_TOOL_OPTIONS = "-Djava.io.tmpdir=$env:TEMP -Duser.home=$localRuntime/home"
$env:PYTHONIOENCODING = 'utf-8'
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
$env:MALL_AI_REVIEWED_FILE = $null

$python = 'F:\softwaretesting\mall-loaal\.venv\Scripts\python.exe'
$allure = Join-Path $localRuntime 'tools\allure-2.42.0\bin\allure.bat'
if (-not (Test-Path -LiteralPath $python)) { throw 'Local Python environment is missing.' }
if (-not (Test-Path -LiteralPath $allure)) { throw 'Local Allure installation is missing.' }

New-Item -ItemType Directory -Force $env:TEMP, '.runtime\ci' | Out-Null
& $python -m pytest .\test_login.py .\test_product.py .\test_category.py -v `
    --alluredir=.runtime/ci/allure-results --clean-alluredir `
    --junitxml=.runtime/ci/junit.xml
$testExit = $LASTEXITCODE

# Generate the report after a failed test as well; preserve pytest's failure status.
& $allure generate '.runtime\ci\allure-results' -o '.runtime\ci\allure-report' --clean
$reportExit = $LASTEXITCODE
if ($testExit -ne 0) { exit $testExit }
exit $reportExit
