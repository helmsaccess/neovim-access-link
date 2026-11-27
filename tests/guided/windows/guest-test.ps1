param([string]$Source, [string]$WorkDir, [IO.Ports.SerialPort]$Serial)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Expand-Input([string]$Name, [string]$Destination) {
    [IO.Compression.ZipFile]::ExtractToDirectory((Join-Path $Source $Name), $Destination)
}
function Send-LoopbackRecording([string]$Path) {
    $wav = Get-Item -LiteralPath $Path
    if ($wav.Length -le 44 -or $wav.Length -gt 16MB) {
        throw 'WASAPI recording is empty or exceeds the transfer limit'
    }
    $hash = (Get-FileHash -LiteralPath $wav.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $compressed = [IO.MemoryStream]::new()
    try {
        $gzip = [IO.Compression.GZipStream]::new($compressed, [IO.Compression.CompressionLevel]::Fastest, $true)
        try {
            $inputStream = [IO.File]::OpenRead($wav.FullName)
            try { $inputStream.CopyTo($gzip) } finally { $inputStream.Dispose() }
        } finally { $gzip.Dispose() }
        if ($compressed.Length -gt 4MB) {
            throw 'Compressed WASAPI recording exceeds the transfer limit'
        }
        $data = $compressed.ToArray()
        $Serial.WriteLine("NAL_WASAPI $($wav.Length) $hash")
        for ($offset = 0; $offset -lt $data.Length; $offset += 1500) {
            $chunk = [Convert]::ToBase64String($data, $offset, [Math]::Min(1500, $data.Length - $offset))
            $Serial.WriteLine("NAL_WASAPI_DATA $offset $chunk")
        }
        $Serial.WriteLine('NAL_WASAPI_END')
    } finally { $compressed.Dispose() }
}
function Save-LazyAuditGitState($Fixture, [string]$Git, [string]$Path) {
    $observed = @{}
    foreach ($entry in $Fixture.initial.PSObject.Properties) {
        $directory = Join-Path $Fixture.root $entry.Name
        if (-not (Test-Path -LiteralPath $directory)) {
            $observed[$entry.Name] = $null
            continue
        }
        $head = & $Git -C $directory rev-parse HEAD
        if ($LASTEXITCODE -ne 0 -or [string]$head -notmatch '^[0-9a-f]{40}$') {
            throw "Could not read fixture HEAD for $($entry.Name)"
        }
        $changes = @(& $Git -C $directory status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw "Could not read fixture status for $($entry.Name)" }
        $observed[$entry.Name] = @{ revision = $head.Trim(); clean = $changes.Count -eq 0 }
    }
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp, ($observed | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Remove-RunToolCopies([string]$Workspace, [string]$RunPath, [string]$RunId) {
    $workspaceRoot = (Resolve-Path -LiteralPath $Workspace).ProviderPath
    $runRoot = (Resolve-Path -LiteralPath $RunPath).ProviderPath
    if ($RunId -notmatch '^[a-f0-9]{12}$' -or $runRoot -ne (Join-Path $workspaceRoot $RunId) -or
        ((Get-Item -LiteralPath $runRoot).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Disposable run directory is outside the guest workspace'
    }
    foreach ($folder in @('nvda', 'editor', 'terminal', 'guided', 'lazy-audit', 'wasapi-tools')) {
        $copy = Join-Path $runRoot $folder
        if (Test-Path -LiteralPath $copy -PathType Container) {
            $resolvedCopy = (Resolve-Path -LiteralPath $copy).ProviderPath
            $item = Get-Item -LiteralPath $resolvedCopy
            if ($resolvedCopy -ne $copy -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'Disposable tool copy is outside its run directory'
            }
            try {
                Remove-Item -LiteralPath $resolvedCopy -Recurse -Force -ErrorAction Stop
            } catch [System.UnauthorizedAccessException], [System.IO.IOException] {
                # Windows can keep an accessibility DLL mapped after NVDA exits.
                $folder
            }
        }
    }
}
$runId = (Get-Content -LiteralPath (Join-Path $Source 'run-id.txt') -TotalCount 1).Trim()
$run = New-Item -ItemType Directory -Force -Path (Join-Path $WorkDir $runId)
$imageStatePath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Setup\State'
$imageState = Get-ItemPropertyValue -LiteralPath $imageStatePath -Name ImageState -ErrorAction SilentlyContinue
if ($env:USERNAME -eq 'NalDesktopTest') {
    $setupDeadline = [DateTime]::UtcNow.AddMinutes(3)
    while ($imageState -ne 'IMAGE_STATE_COMPLETE' -and [DateTime]::UtcNow -lt $setupDeadline) {
        Start-Sleep -Seconds 2
        $imageState = Get-ItemPropertyValue -LiteralPath $imageStatePath -Name ImageState -ErrorAction SilentlyContinue
    }
    if ($imageState -ne 'IMAGE_STATE_COMPLETE') {
        throw "The Windows setup has not finished ($imageState)"
    }
    $powercfg = Join-Path $env:SystemRoot 'System32\powercfg.exe'
    foreach ($idleSetting in @('monitor-timeout-ac', 'standby-timeout-ac')) {
        & $powercfg /change $idleSetting 0
        if ($LASTEXITCODE -ne 0) {
            throw "Could not keep the disposable test desktop active ($idleSetting)"
        }
    }
    $Serial.WriteLine('NAL_SETUP guest display and standby idle timers disabled')
    $previousShutdown = Get-WinEvent -FilterHashtable @{ LogName = 'System'; Id = 1074 } -MaxEvents 1 -ErrorAction SilentlyContinue
    if ($previousShutdown -and $previousShutdown.Properties.Count -gt 0) {
        $Serial.WriteLine("NAL_SETUP last system shutdown $($previousShutdown.TimeCreated.ToString('s')) actor $($previousShutdown.Properties[0].Value)")
    }
    $bootstrapPayload = Join-Path $Source 'bootstrap.ps1'
    if (Test-Path -LiteralPath $bootstrapPayload -PathType Leaf) {
        $bootstrap = Join-Path $WorkDir 'bootstrap.ps1'
        Copy-Item -LiteralPath $bootstrapPayload -Destination $bootstrap -Force
        $startupKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
        if (-not (Test-Path -LiteralPath $startupKey)) {
            New-Item -Path $startupKey | Out-Null
        }
        $launcher = Join-Path $PSHOME 'powershell.exe'
        $startupCommand = '"{0}" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{1}"' -f $launcher, $bootstrap
        Set-ItemProperty -LiteralPath $startupKey -Name 'NalFocusAuditBootstrap' -Value $startupCommand
        $Serial.WriteLine('NAL_SETUP next interactive sign-in will start the test bootstrap')
    }
}
$build = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$Serial.WriteLine("NAL_SETUP Windows build $($build.CurrentBuildNumber).$($build.UBR), image state $imageState")
Get-Process -Name sysprep -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
$redist = Join-Path $Source 'vc-redist.x64.exe'
if (Test-Path -LiteralPath $redist) {
    $Serial.WriteLine('NAL_SETUP Visual C++ runtime')
    $installer = Start-Process -FilePath $redist -ArgumentList '/install', '/quiet', '/norestart' -WindowStyle Hidden -Wait -PassThru
    if ($installer.ExitCode -notin @(0, 1638, 3010)) {
        throw "Visual C++ installation exited with code $($installer.ExitCode)"
    }
}
$toolSource = $null
$reuseFile = Join-Path $Source 'reuse-run.txt'
if (Test-Path -LiteralPath $reuseFile) {
    $previousRun = (Get-Content -LiteralPath $reuseFile -TotalCount 1).Trim()
    if ($previousRun -notmatch '^[a-f0-9]{12}$') { throw 'Invalid test run reference' }
    $toolSource = Join-Path $WorkDir $previousRun
}
if ($toolSource) {
    Copy-Item -LiteralPath (Join-Path $toolSource 'nvda') -Destination (Join-Path $run 'nvda') -Recurse
    Copy-Item -LiteralPath (Join-Path $toolSource 'editor') -Destination (Join-Path $run 'editor') -Recurse
    Copy-Item -LiteralPath (Join-Path $toolSource 'terminal') -Destination (Join-Path $run 'terminal') -Recurse
} else {
    Expand-Input 'nvda.zip' (Join-Path $run 'nvda')
    Expand-Input 'nvim.zip' (Join-Path $run 'editor')
    Expand-Input 'terminal.zip' (Join-Path $run 'terminal')
}
$terminal = Get-ChildItem (Join-Path $run 'terminal') -Filter WindowsTerminal.exe -Recurse | Select-Object -First 1
$terminal.DirectoryName | ForEach-Object { New-Item -Path (Join-Path $_ '.portable') -ItemType File -Force | Out-Null }
$nvim = Get-ChildItem (Join-Path $run 'editor') -Filter nvim.exe -Recurse | Select-Object -First 1
$versionOutput = @(& $nvim.FullName --version)
$versionExit = $LASTEXITCODE
$version = if ($versionOutput.Count) { [string]$versionOutput[0] } else { '' }
if ($versionExit -ne 0 -or $version -notmatch '^NVIM v') {
    throw "Neovim failed to start with $versionExit"
}
$Serial.WriteLine("NAL_SETUP $version")
$pathBeforeTest = $env:Path
$gitGlobalBeforeTest = $env:GIT_CONFIG_GLOBAL
$gitNoSystemBeforeTest = $env:GIT_CONFIG_NOSYSTEM
$gitAttrNoSystemBeforeTest = $env:GIT_ATTR_NOSYSTEM
$gitTemplateBeforeTest = $env:GIT_TEMPLATE_DIR
$env:Path = $nvim.DirectoryName + ';' + $env:Path
$profileDir = New-Item -ItemType Directory -Path (Join-Path $run 'profile')
$addonDir = New-Item -ItemType Directory -Path (Join-Path $profileDir 'addons\NeovimAccessLink')
$candidateProof = Join-Path $Source 'candidate.json'
if (Test-Path -LiteralPath $candidateProof -PathType Leaf) {
    $candidate = Get-Content -LiteralPath $candidateProof -Raw | ConvertFrom-Json
    $actualHash = (Get-FileHash -LiteralPath (Join-Path $Source 'candidate.nvda-addon') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($candidate.sha256 -ne $actualHash) { throw 'The mounted add-on does not match the staged package' }
    $Serial.WriteLine("NAL_SETUP candidate $($candidate.name) SHA256 $actualHash")
}
Expand-Input 'candidate.nvda-addon' $addonDir.FullName
Copy-Item -LiteralPath (Join-Path $Source 'nalAudit.py') -Destination (Join-Path $addonDir 'globalPlugins\nalAudit.py')
$Serial.WriteLine('NAL_SETUP add-on and NVDA observer unpacked')
@"
[general]
    showWelcomeDialogAtStartup = False
[speech]
    synth = silence
[braille]
    display = noBraille
[keyboard]
    NVDAModifierKeys = 4
[update]
    autoCheck = False
"@ | Set-Content -LiteralPath (Join-Path $profileDir 'nvda.ini') -Encoding ascii

$env:NAL_FOCUS_AUDIT = $run.FullName
$env:NAL_FOCUS_TERMINAL = $terminal.FullName
$env:NAL_FOCUS_RUNTIME = Join-Path $addonDir 'globalPlugins\NeovimAccessLink\resources\neovim-plugin'
$env:LOCALAPPDATA = Join-Path $run 'local-app-data'
$env:XDG_CONFIG_HOME = Join-Path $run 'nvim-config'
$env:XDG_DATA_HOME = Join-Path $run 'nvim-data'
$env:XDG_STATE_HOME = Join-Path $run 'nvim-state'
$env:XDG_CACHE_HOME = Join-Path $run 'nvim-cache'
$log = Join-Path $run 'nvda.log'
$events = Join-Path $run 'steps.log'
$report = Join-Path $run 'result.json'
$nvdaProgram = Join-Path $run 'nvda\nvda_noUIAccess.exe'
if (Test-Path -LiteralPath (Join-Path $Source 'uiaccess.txt')) {
    $programDir = Join-Path $env:ProgramFiles "NalFocusAuditNvda-$runId"
    Copy-Item -LiteralPath (Join-Path $run 'nvda') -Destination $programDir -Recurse
    $nvdaProgram = Join-Path $programDir 'nvda.exe'
    $signature = Get-AuthenticodeSignature -LiteralPath $nvdaProgram
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'NV Access') {
        throw "The guest could not verify the signed NVDA executable: $($signature.Status)"
    }
    $Serial.WriteLine('NAL_SETUP signed NVDA UIAccess from Program Files')
}
$nvda = $null
$lazyCase = $null
$loopback = $null
$discardCopies = $toolSource -and $previousRun -ne $runId -and
    (Test-Path -LiteralPath (Join-Path $Source 'discard-run-copies.txt') -PathType Leaf)
$completed = $false
try {
    $init = Join-Path $run 'init.lua'
    $firstEditor = Join-Path $run 'A.txt'
    @'
    vim.opt.loadplugins = false
    vim.opt.rtp:prepend(vim.env.NAL_FOCUS_RUNTIME)
    vim.cmd("runtime plugin/nvim_nvda.lua")
'@ | Set-Content -LiteralPath $init -Encoding ascii
    'nal editor A' | Set-Content -LiteralPath $firstEditor -Encoding ascii
    $env:NAL_FOCUS_PRESTART = '1'
    $launch = @('--window', 'NalPrimary', 'new-tab', '--title', '"NAL Editor A"', '--suppressApplicationTitle',
        '--inheritEnvironment', $nvim.FullName, '-u', $init, '-i', 'NONE', '-n', $firstEditor)
    if (Test-Path -LiteralPath (Join-Path $Source 'guided.zip')) {
        $guided = Join-Path $run 'guided'
        Expand-Input 'guided.zip' $guided
        $Serial.WriteLine('NAL_SETUP guided fixture unpacked')
        $env:NAL_FOCUS_GUIDED = '1'
        $env:ACCESS_LINK_HUMAN_DRY_RUN = '1'
        $env:ACCESS_LINK_HUMAN_PROFILE = 'focus'
        $env:ACCESS_LINK_HUMAN_TEST_ID = 'S1'
        $env:ACCESS_LINK_HUMAN_STEP_ID = 'focus-and-disconnect'
        $env:NAL_FOCUS_GUIDED_ROOT = $guided
        $env:NAL_FOCUS_GUIDED_NVIM = $nvim.FullName
        $env:NAL_FOCUS_EDITOR_FILE = 'lsp_features.py'
        $diagnosticAudio = Test-Path -LiteralPath (Join-Path $guided 'audio-d1.txt')
        $clangAudio = Test-Path -LiteralPath (Join-Path $guided 'audio-d3.txt')
        $markdownAudio = Test-Path -LiteralPath (Join-Path $guided 'audio-d4.txt')
        $externalAudio = $clangAudio -or $markdownAudio
        $heldSignature = Test-Path -LiteralPath (Join-Path $guided 'held-l3.txt')
        $lazyCasePath = Join-Path $guided 'lazy-case.txt'
        $lazyCase = if (Test-Path -LiteralPath $lazyCasePath) {
            (Get-Content -LiteralPath $lazyCasePath -Raw).Trim()
        }
        $lazySteps = @{ P1 = 'lazy-window'; P2 = 'lazy-install'; P3 = 'lazy-update'; P4 = 'lazy-sync' }
        if ($lazyCase -and -not $lazySteps.ContainsKey($lazyCase)) { throw 'Unknown lazy.nvim case' }
        $nativeLspPath = Join-Path $guided 'native-lsp-profile.txt'
        $nativeLsp = if (Test-Path -LiteralPath $nativeLspPath) {
            (Get-Content -LiteralPath $nativeLspPath -Raw).Trim()
        }
        $nativeSteps = @{
            L1 = 'status-presentation'; L2 = 'automatic-parameters'
            L4 = 'native-search-replacement'; L5 = 'native-lsp-rename'; L6 = 'native-buffer-replacement'
        }
        if ($nativeLsp -and -not $nativeSteps.ContainsKey($nativeLsp)) { throw 'Unknown native LSP scenario' }
        if ($diagnosticAudio -or $externalAudio -or $heldSignature -or $nativeLsp -or $lazyCase -or (Test-Path -LiteralPath (Join-Path $guided 'audio-c1.txt'))) {
            $env:NAL_FOCUS_GUIDED = 'audio-c1'
            $env:ACCESS_LINK_HUMAN_DRY_RUN = '0'
            $env:ACCESS_LINK_HUMAN_PROFILE = 'native'
            $env:ACCESS_LINK_HUMAN_TEST_ID = 'C1'
            $env:ACCESS_LINK_HUMAN_STEP_ID = 'completion-presentation'
            $env:ACCESS_LINK_HUMAN_PLUGIN = $env:NAL_FOCUS_RUNTIME
            $env:ACCESS_LINK_HUMAN_DEPENDENCIES = Join-Path $guided 'dependencies.json'
            $env:ACCESS_LINK_HUMAN_PYRIGHT = Join-Path $guided 'pyright\langserver.index.js'
            $env:NAL_FOCUS_EDITOR_STATE = Join-Path $run 'editor-audio-state.json'
            $env:Path = "$guided;$env:Path"
            $completionProfilePath = Join-Path $guided 'completion-profile.txt'
            $completionProfile = $null
            if (Test-Path -LiteralPath $completionProfilePath) {
                $completionProfile = (Get-Content -LiteralPath $completionProfilePath -Raw).Trim()
                if ($completionProfile -notin @('cmp', 'blink')) { throw "Unknown completion profile" }
                $env:ACCESS_LINK_HUMAN_PROFILE = $completionProfile
                $env:ACCESS_LINK_HUMAN_TEST_ID = if ($completionProfile -eq 'cmp') { 'C2' } else { 'C3' }
                $env:ACCESS_LINK_HUMAN_STEP_ID = 'menu-presentation'
            }
            if ($diagnosticAudio -or $externalAudio -or $completionProfile -or $lazyCase) {
                $env:XDG_DATA_HOME = Join-Path $guided 'data'
                $env:XDG_CONFIG_HOME = Join-Path $guided 'config'
                $gitBin = Join-Path $guided $(if ($lazyCase) { 'git-mingit\cmd' } else { 'git-bin' })
                $env:Path = "$gitBin;$env:Path"
                $env:GIT_CONFIG_NOSYSTEM = '1'
                $env:GIT_ATTR_NOSYSTEM = '1'
                $env:GIT_CONFIG_GLOBAL = Join-Path $run 'isolated-gitconfig'
                New-Item -ItemType File -Path $env:GIT_CONFIG_GLOBAL | Out-Null
                & (Join-Path $gitBin 'git.exe') --version | ForEach-Object { $Serial.WriteLine("NAL_SETUP $_") }
                if ($LASTEXITCODE -ne 0) { throw 'Git could not start in the guest' }
            }
            if ($lazyCase) {
                $env:NAL_FOCUS_GUIDED = 'lazy-' + $lazyCase.ToLowerInvariant()
                $env:ACCESS_LINK_HUMAN_PROFILE = 'lazy'
                $env:ACCESS_LINK_HUMAN_TEST_ID = $lazyCase
                $env:ACCESS_LINK_HUMAN_STEP_ID = $lazySteps[$lazyCase]
                $env:NAL_FOCUS_EDITOR_FILE = 'lazy-test.txt'
                $fixtureScript = Join-Path $guided 'prepare-lazy-fixture.ps1'
                $git = Join-Path $gitBin 'git.exe'
                $env:ACCESS_LINK_HUMAN_LAZY_FIXTURE = & $fixtureScript -Case $lazyCase -Root (Join-Path $run 'lazy-audit') -Seeds $guided -Git $git
                $lazyFixture = Get-Content -LiteralPath $env:ACCESS_LINK_HUMAN_LAZY_FIXTURE -Raw | ConvertFrom-Json
                Save-LazyAuditGitState $lazyFixture $git (Join-Path $run 'lazy-git-before.json')
                $Serial.WriteLine('NAL_SETUP offline Git fixtures prepared and independently observed')
            }
            if ($nativeLsp) {
                $env:NAL_FOCUS_GUIDED = 'lsp-' + $nativeLsp.ToLowerInvariant()
                $env:ACCESS_LINK_HUMAN_TEST_ID = $nativeLsp
                $env:ACCESS_LINK_HUMAN_STEP_ID = $nativeSteps[$nativeLsp]
                if ($nativeLsp -in @('L4', 'L6')) { $env:ACCESS_LINK_HUMAN_DRY_RUN = '1' }
                if (Test-Path -LiteralPath (Join-Path $guided 'lsp-hints-disabled.txt')) {
                    @'
[NeovimAccessLink]
    automaticParameterHints = False
'@ | Add-Content -LiteralPath (Join-Path $profileDir 'nvda.ini') -Encoding ascii
                }
            }
            if ($heldSignature) {
                $env:NAL_FOCUS_GUIDED = 'held-l3'
                $env:ACCESS_LINK_HUMAN_TEST_ID = 'L3'
                $env:ACCESS_LINK_HUMAN_STEP_ID = 'held-parameters'
            }
            $nativeCompletion = -not $completionProfile -and (Test-Path -LiteralPath (Join-Path $guided 'audio-c1.txt'))
            if ($heldSignature -or $nativeLsp -eq 'L2' -or $lazyCase -eq 'P1' -or $nativeCompletion) {
                $iniPath = Join-Path $profileDir 'nvda.ini'
                $ini = [IO.File]::ReadAllText($iniPath)
                $ini.Replace('    display = noBraille', "    display = noBraille`r`n    showCursor = False`r`n    translationTable = en-us-comp8-ext.utb") |
                    Set-Content -LiteralPath $iniPath -Encoding ascii
            }
            if ($externalAudio) {
                if ($clangAudio) {
                    $env:NAL_FOCUS_GUIDED = 'audio-d3'
                    $env:ACCESS_LINK_HUMAN_PROFILE = 'c-diagnostics'
                    $env:ACCESS_LINK_HUMAN_TEST_ID = 'D3'
                    $env:ACCESS_LINK_HUMAN_STEP_ID = 'clang-tidy-presentation'
                    $env:NAL_FOCUS_EDITOR_FILE = 'diagnostics.c'
                    $env:ACCESS_LINK_HUMAN_CLANG_TIDY = Join-Path $guided 'clang-tidy.exe'
                } else {
                    $env:NAL_FOCUS_GUIDED = 'audio-d4'
                    $env:ACCESS_LINK_HUMAN_PROFILE = 'markdown-diagnostics'
                    $env:ACCESS_LINK_HUMAN_TEST_ID = 'D4'
                    $env:ACCESS_LINK_HUMAN_STEP_ID = 'markdownlint-presentation'
                    $env:NAL_FOCUS_EDITOR_FILE = 'diagnostics.md'
                    $env:ACCESS_LINK_HUMAN_MARKDOWNLINT = Join-Path $guided 'node_modules\.bin\markdownlint-cli2.cmd'
                }
                $card = Get-Content -LiteralPath (Join-Path $guided 'diagnostic-card.json') -Raw | ConvertFrom-Json
                $env:ACCESS_LINK_HUMAN_PURPOSE = $card.purpose
                $env:ACCESS_LINK_HUMAN_TASK = $card.action
                $env:ACCESS_LINK_HUMAN_EXPECTED = $card.expected
            }
            if ($diagnosticAudio) {
                $env:NAL_FOCUS_GUIDED = 'audio-d1'
                $env:ACCESS_LINK_HUMAN_PROFILE = 'diagnostics'
                $env:ACCESS_LINK_HUMAN_TEST_ID = 'D1'
                $env:ACCESS_LINK_HUMAN_STEP_ID = 'navigation-presentation'
                $env:NAL_FOCUS_EDITOR_FILE = 'diagnostics.py'
                $env:ACCESS_LINK_HUMAN_RUFF = Join-Path $guided 'ruff.exe'
                if (Test-Path -LiteralPath (Join-Path $guided 'held-d2.txt')) {
                    $env:NAL_FOCUS_GUIDED = 'held-d2'
                    $env:ACCESS_LINK_HUMAN_TEST_ID = 'D2'
                    $env:ACCESS_LINK_HUMAN_STEP_ID = 'held-diagnostics'
                    $iniPath = Join-Path $profileDir 'nvda.ini'
                    $ini = [IO.File]::ReadAllText($iniPath)
                    $ini.Replace('    display = noBraille', "    display = noBraille`r`n    showCursor = False`r`n    translationTable = en-us-comp8-ext.utb") |
                        Set-Content -LiteralPath $iniPath -Encoding ascii
                }
            }
            if (Test-Path -LiteralPath (Join-Path $guided 'audio-d1-muted.txt')) {
                    @'
[NeovimAccessLink]
    [[feedback]]
        diagnosticLine = 0
        diagnosticPosition = 0
'@ | Add-Content -LiteralPath (Join-Path $profileDir 'nvda.ini') -Encoding ascii
            }
            if (Test-Path -LiteralPath (Join-Path $guided 'audio-c1-muted.txt')) {
                @'
[presentation]
    reportAutoSuggestionsWithSound = False
'@ | Add-Content -LiteralPath (Join-Path $profileDir 'nvda.ini') -Encoding ascii
            }
        }
        $shell = Join-Path $PSHOME 'powershell.exe'
        $settingsDir = New-Item -ItemType Directory -Force -Path (Join-Path $terminal.DirectoryName 'settings')
        $profileId = '{31c41e6a-b8d8-403b-9706-d742ca145db4}'
        @{
            defaultProfile = $profileId
            profiles = @{ list = @(@{
                guid = $profileId
                name = 'NAL Unclaimed PowerShell'
                commandline = "$shell -NoLogo -NoProfile -NoExit -Command `"Import-Module PSReadLine`""
                tabTitle = 'NAL Unclaimed PowerShell'
                suppressApplicationTitle = $true
            }) }
            actions = @(
                @{ command = 'newTab'; keys = 'ctrl+shift+t' }
                @{ command = @{ action = 'switchToTab'; index = 0 }; keys = 'ctrl+alt+1' }
            )
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $settingsDir 'settings.json') -Encoding ascii
        $wrapper = Join-Path $guided 'start.ps1'
        @'
Import-Module PSReadLine
Set-Location -LiteralPath $env:NAL_FOCUS_GUIDED_ROOT
& $env:NAL_FOCUS_GUIDED_NVIM --cmd 'lua vim.opt.runtimepath:prepend(vim.env.NAL_FOCUS_RUNTIME)' -u init.lua -i NONE -n $env:NAL_FOCUS_EDITOR_FILE
'@ | Set-Content -LiteralPath $wrapper -Encoding ascii
        $launch = @('--window', 'new', 'new-tab', '--title', '"NAL Editor A"', '--suppressApplicationTitle',
            '--inheritEnvironment')
        if ($env:NAL_FOCUS_GUIDED -match '^(audio|held|lsp|lazy)-') {
            $wrapper = Join-Path $guided 'start.cmd'
            @'
@echo off
cd /d "%NAL_FOCUS_GUIDED_ROOT%"
"%NAL_FOCUS_GUIDED_NVIM%" --cmd "lua vim.opt.runtimepath:prepend(vim.env.NAL_FOCUS_RUNTIME)" --cmd "luafile audio-neovim-observer.lua" -u init.lua -i NONE -n "%NAL_FOCUS_EDITOR_FILE%"
set "editorStatus=%errorlevel%"
> "%NAL_FOCUS_EDITOR_STATE%" echo {"exitCode": %editorStatus%}
exit /b %editorStatus%
'@ | Set-Content -LiteralPath $wrapper -Encoding ascii
            $launch += @((Join-Path $env:SystemRoot 'System32\cmd.exe'), '/d', '/c', $wrapper)
        } else {
            $launch += @($shell, '-NoLogo', '-NoProfile', '-NoExit',
                '-ExecutionPolicy', 'Bypass', '-File', $wrapper)
        }
    }
    $terminalLaunchTime = Get-Date
    $startedTerminal = Start-Process -FilePath $terminal.FullName -WorkingDirectory $terminal.DirectoryName -ArgumentList $launch -PassThru
    $Serial.WriteLine('NAL_SETUP Windows Terminal launch requested')
    Start-Sleep -Seconds 7
    if (Test-Path -LiteralPath (Join-Path $Source 'guided.zip')) {
        $ownsEditorWindow = {
            Get-Process -Name WindowsTerminal -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -like "$run\*" -and $_.MainWindowTitle -like '*NAL Editor A*' }
        }
        $until = [DateTime]::UtcNow.AddSeconds(25)
        while (-not (& $ownsEditorWindow) -and [DateTime]::UtcNow -lt $until) {
            Start-Sleep -Milliseconds 500
        }
        if (-not (& $ownsEditorWindow)) {
            $detail = if ($startedTerminal.HasExited) { $startedTerminal.ExitCode } else { 'running' }
            $Serial.WriteLine("NAL_SETUP initial Terminal did not expose its editor window ($detail); retry")
            Start-Process -FilePath $terminal.FullName -WorkingDirectory $terminal.DirectoryName -ArgumentList $launch | Out-Null
        }
    }
    $nvdaArgs = @('--minimal', '--debug-logging', '--config-path', $profileDir.FullName, '--log-file', $log)
    if ($nvdaProgram.EndsWith('nvda_noUIAccess.exe')) { $nvdaArgs += '--no-sr-flag' }
    if (Test-Path -LiteralPath (Join-Path $Source 'wasapi-tools.zip')) {
        $loopbackTools = Join-Path $run 'wasapi-tools'
        $loopbackLog = Join-Path $run 'wasapi.error'
        Expand-Input 'wasapi-tools.zip' $loopbackTools
        $loopback = Start-Process -FilePath (Join-Path $loopbackTools 'wasapi-loopback-probe.exe') `
            -ArgumentList ('"{0}"' -f $run.FullName) -WindowStyle Hidden -PassThru -RedirectStandardError $loopbackLog
        $ready = Join-Path $run 'wasapi.ready'
        $deadline = [DateTime]::UtcNow.AddSeconds(40)
        while (-not $loopback.HasExited -and -not (Test-Path -LiteralPath $ready) -and [DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Milliseconds 200
        }
        if ($loopback.HasExited -or -not (Test-Path -LiteralPath $ready)) {
            throw "WASAPI loopback probe did not start. $(Get-Content -LiteralPath $loopbackLog -Raw)"
        }
        $Serial.WriteLine('NAL_SETUP WASAPI render endpoint loopback started')
    }
    $nvda = Start-Process -FilePath $nvdaProgram -ArgumentList $nvdaArgs -PassThru
    $Serial.WriteLine('NAL_SETUP NVDA launch requested')
    $last = 0
    $stopAt = [DateTime]::UtcNow.AddMinutes(9)
    while ([DateTime]::UtcNow -lt $stopAt) {
        if (Test-Path -LiteralPath $events) {
            $lines = @(Get-Content -LiteralPath $events)
            while ($last -lt $lines.Count) {
                $Serial.WriteLine($lines[$last])
                if ($lazyCase -and $lines[$last] -eq 'NAL_GIT snapshot-after') {
                    Save-LazyAuditGitState $lazyFixture $git (Join-Path $run 'lazy-git-after.json')
                }
                $last++
            }
        }
        if (Test-Path -LiteralPath $report) {
            $payload = (Get-Content -LiteralPath $report -Raw).Trim()
            $guestPassed = (ConvertFrom-Json -InputObject $payload).ok
            if (-not $guestPassed) {
                $launchStatus = if ($startedTerminal.HasExited) { "exit=$($startedTerminal.ExitCode)" } else { 'running' }
                $processes = @(Get-Process -Name WindowsTerminal,nvim -ErrorAction SilentlyContinue |
                    Where-Object { $_.Path -like "$run\*" } | ForEach-Object { "$($_.ProcessName):$($_.Id)" })
                $Serial.WriteLine("NAL_DIAG Terminal launcher $($startedTerminal.Id) $launchStatus; guest editor processes: $($processes -join ', ')")
                Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000,1001,1002; StartTime = $terminalLaunchTime } `
                    -MaxEvents 30 -ErrorAction SilentlyContinue |
                    Where-Object { $_.Message -match '(?i)\b(WindowsTerminal|nvim)\.exe\b' } | Select-Object -First 3 |
                    ForEach-Object {
                        $detail = $_.Message -split '\r?\n' | Select-Object -First 7
                        $Serial.WriteLine("NAL_DIAG $($_.ProviderName) event $($_.Id): $($detail -join ' | ')")
                    }
                Get-Content -LiteralPath $log -Tail 55 | ForEach-Object { $Serial.WriteLine('NAL_LOG ' + $_) }
            }
            $Serial.WriteLine('NAL_RESULT ' + $payload)
            if ($loopback) {
                New-Item -ItemType File -Path (Join-Path $run 'wasapi.stop') | Out-Null
                $complete = Join-Path $run 'wasapi.complete'
                if (-not $loopback.WaitForExit(40000)) {
                    throw 'WASAPI loopback process did not exit after receiving the stop signal'
                }
                if (-not (Test-Path -LiteralPath $complete -PathType Leaf)) {
                    throw "WASAPI loopback exited without finalizing the WAV (exit $($loopback.ExitCode)). $(Get-Content -LiteralPath $loopbackLog -Raw)"
                }
                Send-LoopbackRecording (Join-Path $run 'wasapi.wav')
            }
            $completed = $guestPassed
            return
        }
        if ($nvda.HasExited) { throw "NVDA exited with code $($nvda.ExitCode)" }
        Start-Sleep -Milliseconds 350
    }
    throw 'Guest test execution timed out'
} catch {
    if (Test-Path -LiteralPath $log) {
        Get-Content -LiteralPath $log -Tail 45 | ForEach-Object { $Serial.WriteLine('NAL_LOG ' + $_) }
    }
    throw
} finally {
    Remove-Item Env:NAL_FOCUS_GUIDED -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_DRY_RUN -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_PROFILE -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_TEST_ID -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_STEP_ID -ErrorAction SilentlyContinue
    Remove-Item Env:NAL_FOCUS_GUIDED_ROOT -ErrorAction SilentlyContinue
    Remove-Item Env:NAL_FOCUS_GUIDED_NVIM -ErrorAction SilentlyContinue
    Remove-Item Env:NAL_FOCUS_EDITOR_STATE -ErrorAction SilentlyContinue
    Remove-Item Env:NAL_FOCUS_EDITOR_FILE -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_RUFF -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_CLANG_TIDY -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_MARKDOWNLINT -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_PURPOSE -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_TASK -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_EXPECTED -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_PLUGIN -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_DEPENDENCIES -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_PYRIGHT -ErrorAction SilentlyContinue
    Remove-Item Env:ACCESS_LINK_HUMAN_LAZY_FIXTURE -ErrorAction SilentlyContinue
    $env:Path = $pathBeforeTest
    $env:GIT_CONFIG_GLOBAL = $gitGlobalBeforeTest
    $env:GIT_CONFIG_NOSYSTEM = $gitNoSystemBeforeTest
    $env:GIT_ATTR_NOSYSTEM = $gitAttrNoSystemBeforeTest
    $env:GIT_TEMPLATE_DIR = $gitTemplateBeforeTest
    if ($nvda -and -not $nvda.HasExited) {
        if (-not $nvda.WaitForExit(3000)) { Stop-Process -Id $nvda.Id -ErrorAction SilentlyContinue }
    }
    if ($loopback -and -not $loopback.HasExited) {
        Stop-Process -Id $loopback.Id -ErrorAction SilentlyContinue
    }
    Get-Process -Name WindowsTerminal,nvim -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$run\*" } | Stop-Process -ErrorAction SilentlyContinue
    if ($discardCopies -and $completed) {
        $deferred = @(Remove-RunToolCopies $WorkDir $run.FullName $runId)
        if ($deferred.Count) {
            $Serial.WriteLine("NAL_CLEAN deferred tool and fixture copies: $($deferred -join ', ')")
        } else {
            $Serial.WriteLine('NAL_CLEAN finished run tool and fixture copies removed')
        }
    }
}
