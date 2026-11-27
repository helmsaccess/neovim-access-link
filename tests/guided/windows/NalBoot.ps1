$ErrorActionPreference = 'Stop'
$serial = [IO.Ports.SerialPort]::new('COM1', 115200, 'None', 8, 'One')
$serial.Open()
try {
    $working = New-Item -ItemType Directory -Force -Path 'C:\NalFocusAudit'
    $serial.WriteLine('NAL_BOOT audit desktop ready')
    $lastRun = $null
    while ($true) {
        $media = Get-Volume -FileSystemLabel NALPAYLOAD -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($media -and $media.DriveLetter) {
            $source = $media.DriveLetter + ':\'
            if (Test-Path -LiteralPath (Join-Path $source 'run-id.txt')) {
                $runId = (Get-Content -LiteralPath (Join-Path $source 'run-id.txt') -TotalCount 1).Trim()
                if ($runId -match '^[a-zA-Z0-9_-]+$' -and $runId -ne $lastRun) {
                    $lastRun = $runId
                    if (Test-Path -LiteralPath (Join-Path $working.FullName $runId)) {
                        $serial.WriteLine("NAL_SKIP already started $runId")
                        continue
                    }
                    $serial.WriteLine("NAL_START $runId")
                    try {
                        & (Join-Path $source 'guest-test.ps1') -Source $source -WorkDir $working.FullName -Serial $serial
                        $serial.WriteLine("NAL_END $runId")
                    } catch {
                        $serial.WriteLine("NAL_ERROR " + $_.Exception.Message)
                        $serial.WriteLine($_.ScriptStackTrace)
                    }
                }
            }
        }
        Start-Sleep -Seconds 4
    }
} finally {
    $serial.Dispose()
}
