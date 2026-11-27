param([string]$Source, [string]$WorkDir, [IO.Ports.SerialPort]$Serial)

$ErrorActionPreference = 'Stop'
function Play-Reference([string]$Name) {
    $player = [System.Media.SoundPlayer]::new((Join-Path $Source "$Name.wav"))
    try {
        $player.Load()
        $player.PlaySync()
    } finally {
        $player.Dispose()
    }
    Start-Sleep -Milliseconds 260
}

Start-Service AudioEndpointBuilder
Start-Service Audiosrv
$Serial.WriteLine('NAL_AUDIO calibration rendering started')
foreach ($name in 'begin', 'open', 'close', 'warning', 'error', 'none', 'end') {
    Play-Reference $name
}
$Serial.WriteLine('NAL_AUDIO calibration rendering finished')
