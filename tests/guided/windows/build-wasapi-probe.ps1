param(
    [Parameter(Mandatory)][string]$PackageDirectory
)

$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$vm=$PSScriptRoot
$toolsDir=(Resolve-Path -LiteralPath $PackageDirectory).Path
$expected=@{
 'NAudio.Core'='794645DBFD30E4880663D52D9D9224D55C301FA54228FF623C95D572C7887347'
 'NAudio.Wasapi'='C8396B8DBAB86A2619EDFD9158BEAF18C21CB86677099B5594950FD8651B9D1A'
}
foreach($package in $expected.Keys){
    $archivePath=Join-Path $toolsDir "$($package.ToLowerInvariant()).2.2.1.nupkg"
    if((Get-FileHash -LiteralPath $archivePath).Hash -ne $expected[$package]){throw "Unexpected hash for $package"}
    $archive=[IO.Compression.ZipFile]::OpenRead($archivePath)
    try { [IO.Compression.ZipFileExtensions]::ExtractToFile($archive.GetEntry("lib/netstandard2.0/$package.dll"),(Join-Path $toolsDir "$package.dll"),$true) }
    finally { $archive.Dispose() }
}
$framework='C:\Windows\Microsoft.NET\Framework64\v4.0.30319'
& (Join-Path $framework 'csc.exe') /nologo /target:exe "/out:$toolsDir\wasapi-loopback-probe.exe" "/reference:$framework\netstandard.dll" "/reference:$toolsDir\NAudio.Core.dll" "/reference:$toolsDir\NAudio.Wasapi.dll" (Join-Path $vm 'wasapi-loopback-probe.cs')
exit $LASTEXITCODE
