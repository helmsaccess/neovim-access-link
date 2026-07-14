param(
    [switch]$UseSftp,
    [string]$Destination = "",
    [string]$RemoteBase = "/tmp"
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$candidates = @(
    (Join-Path $env:TEMP "nvda-old.log"),
    (Join-Path $env:TEMP "nvda.log")
) | Where-Object { Test-Path $_ }

if ($candidates.Count -eq 0) {
    throw "No nvda.log or nvda-old.log found below $env:TEMP"
}

if (-not $UseSftp) {
    # When the project is mounted as X:, copying into the shared workspace is
    # simpler and safer than invoking SSH from inside a diagnostic workflow.
    $repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
    $localDirectory = Join-Path $repositoryRoot "debug\incoming\nvda-$stamp"
    New-Item -ItemType Directory -Path $localDirectory -Force | Out-Null
    foreach ($logFile in $candidates) {
        Copy-Item -LiteralPath $logFile -Destination $localDirectory -Force
    }
    Write-Host "Copied NVDA logs to $localDirectory"
    exit 0
}

# Optional network path. SFTP uses the SSH subsystem and is not corrupted by
# output from interactive shell startup files, unlike legacy SCP.
if ([string]::IsNullOrWhiteSpace($Destination)) {
    throw "Destination is required with -UseSftp, for example editor@example.invalid"
}

$remoteDirectory = "$RemoteBase/nvim-nvda-session-$stamp"
& ssh $Destination "mkdir -p '$remoteDirectory' && chmod 700 '$remoteDirectory'"
if ($LASTEXITCODE -ne 0) {
    throw "ssh failed with exit code $LASTEXITCODE"
}

$batchFile = Join-Path $env:TEMP "nvim-nvda-sftp-$stamp.txt"
try {
    $commands = foreach ($logFile in $candidates) {
        $local = $logFile.Replace("\", "/")
        $name = [System.IO.Path]::GetFileName($logFile)
        "put `"$local`" `"$remoteDirectory/$name`""
    }
    Set-Content -LiteralPath $batchFile -Value $commands -Encoding ascii
    & sftp -b $batchFile $Destination
    if ($LASTEXITCODE -ne 0) {
        throw "sftp failed with exit code $LASTEXITCODE"
    }
} finally {
    Remove-Item -LiteralPath $batchFile -Force -ErrorAction SilentlyContinue
}

Write-Host "Uploaded NVDA logs to ${Destination}:${remoteDirectory}"
