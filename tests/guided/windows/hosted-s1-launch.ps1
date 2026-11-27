param(
    [Parameter(Mandatory)][string]$Source,
    [Parameter(Mandatory)][string]$WorkDir,
    [Parameter(Mandatory)][string]$Transcript
)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'The hosted test requires a disposable GitHub-hosted Windows runner'
}
if (Get-Process -Name nvda,nvda_noUIAccess -ErrorAction SilentlyContinue) {
    throw 'The hosted test requires an unused NVDA desktop'
}
$runId = (Get-Content -LiteralPath (Join-Path $Source 'run-id.txt') -TotalCount 1).Trim()
if ($runId -notmatch '^[a-f0-9]{12}$' -or (Test-Path -LiteralPath (Join-Path $WorkDir $runId))) {
    throw 'The hosted test requires a fresh run'
}
$stream = [IO.File]::Open($Transcript, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite)
$writer = [IO.StreamWriter]::new($stream, [Text.Encoding]::ASCII)
$writer.AutoFlush = $true
try {
    $writer.WriteLine("NAL_START $runId")
    & (Join-Path $Source 'guest-test.ps1') -Source $Source -WorkDir $WorkDir -Serial $writer -HostedDesktop
    $writer.WriteLine("NAL_END $runId")
} catch {
    $writer.WriteLine('NAL_ERROR ' + $_.Exception.Message)
    $writer.WriteLine($_.ScriptStackTrace)
    throw
} finally {
    $writer.Dispose()
}
