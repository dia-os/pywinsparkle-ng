# Build upstream WinSparkle with this repository's patches; no GitHub fork required.
[CmdletBinding()]
param(
    [string]$NuGet = 'nuget',
    [string]$MSBuild = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'winsparkle.json') -Raw | ConvertFrom-Json
$sourceDir = Join-Path $repoRoot "build/winsparkle-$($config.version)"

function Invoke-Native {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE"
    }
}

# Resolve prerequisites before downloading sources or modifying the checkout.
$null = Get-Command git -ErrorAction Stop
$nugetExe = (Get-Command $NuGet -ErrorAction Stop).Source
if (-not $MSBuild) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswhere)) {
        throw 'Install Visual Studio 2022 with Desktop development with C++ and a Windows SDK.'
    }
    $MSBuild = & $vswhere -latest -products '*' -version '[17.0,18.0)' `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
    if (-not $MSBuild) {
        throw 'Visual Studio 2022 C++ tools were not found.'
    }
}
$msbuildExe = (Get-Command $MSBuild -ErrorAction Stop).Source

if (-not (Test-Path -LiteralPath $sourceDir)) {
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $sourceDir) -Force
    Invoke-Native git @('clone', '--branch', "v$($config.version)", '--depth', '1', $config.source_url, $sourceDir)
}
if (-not (Test-Path -LiteralPath (Join-Path $sourceDir '.git'))) {
    throw "Expected an upstream Git checkout at $sourceDir"
}
$revision = & git -C $sourceDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $revision -ne $config.source_revision) {
    throw "Source revision mismatch: expected $($config.source_revision), got $revision. Use a fresh build directory."
}

# Accept only a clean checkout or exactly our patch, so a repeated build is safe.
$patchPaths = @($config.patches | ForEach-Object { Join-Path $repoRoot $_ })
$savedErrorActionPreference = $ErrorActionPreference
try {
    # Windows PowerShell treats native stderr as errors, even for this probe.
    $ErrorActionPreference = 'Continue'
    & git -C $sourceDir apply --reverse --check @patchPaths 2>$null
    $alreadyPatched = $LASTEXITCODE -eq 0
} finally {
    $ErrorActionPreference = $savedErrorActionPreference
}
if ($alreadyPatched) {
    # Temporarily reverse our patch to detect any unrelated tracked edits.
    Invoke-Native git (@('-C', $sourceDir, 'apply', '--reverse') + $patchPaths)
    try {
        & git -C $sourceDir diff --quiet HEAD --
        $unexpectedChanges = $LASTEXITCODE -ne 0
    } finally {
        Invoke-Native git (@('-C', $sourceDir, 'apply') + $patchPaths)
    }
    if ($unexpectedChanges) {
        throw 'Unexpected source changes. Use a fresh build directory.'
    }
} else {
    $localChanges = @(& git -C $sourceDir status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $localChanges.Count -ne 0) {
        throw 'The source checkout has local changes. Use a fresh build directory.'
    }
    Invoke-Native git (@('-C', $sourceDir, 'apply', '--check') + $patchPaths)
    Invoke-Native git (@('-C', $sourceDir, 'apply') + $patchPaths)
}
Invoke-Native git @('-C', $sourceDir, 'submodule', 'update', '--init', '--recursive', '--depth', '1')

Push-Location $sourceDir
try {
    Invoke-Native $nugetExe @('restore', 'WinSparkle.sln', '-PackagesDirectory', 'packages', '-NonInteractive', '-DirectDownload')
    # Build only the DLL and its dependencies, using upstream's supported VS2022 toolset.
    Invoke-Native $msbuildExe @('WinSparkle.sln', '-m', '-t:WinSparkle', '-p:Configuration=Release', '-p:Platform=x64', '-p:PlatformToolset=v143', '-verbosity:minimal')
} finally {
    Pop-Location
}

$builtDll = Join-Path $sourceDir 'x64/Release/WinSparkle.dll'
if (-not (Test-Path -LiteralPath $builtDll)) {
    throw "Build did not produce $builtDll"
}
$destination = Join-Path $repoRoot 'pywinsparkle/libs/x64'
$null = New-Item -ItemType Directory -Path $destination -Force
Copy-Item -LiteralPath (Join-Path $sourceDir 'COPYING') -Destination (Join-Path $destination 'COPYING') -Force
# Match the notice included by upstream's binary distribution makefile.
Copy-Item -LiteralPath (Join-Path $sourceDir '3rdparty/expat/expat/COPYING') -Destination (Join-Path $destination 'COPYING.expat') -Force
Copy-Item -LiteralPath $builtDll -Destination (Join-Path $destination 'WinSparkle.dll') -Force
$patchDigests = @($patchPaths | ForEach-Object {
    [ordered]@{ name = Split-Path -Leaf $_; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant() }
})
[ordered]@{
    version = $config.version
    source_url = $config.source_url
    source_revision = $revision
    patches = $patchDigests
    dll_sha256 = (Get-FileHash -LiteralPath $builtDll -Algorithm SHA256).Hash.ToLowerInvariant()
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $destination 'native-build.json') -Encoding UTF8
Write-Host "Bundled patched WinSparkle $($config.version) x64 DLL: $destination"
