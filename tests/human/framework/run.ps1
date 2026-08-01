[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("menu", "run", "setup", "list", "verify", "clean")]
    [string]$Action = "menu",

    [ValidateSet("smoke", "compatibility", "all")]
    [string]$Suite = "smoke",

    [ValidateSet("auto", "de", "en")]
    [string]$Language = "auto",

    [string]$ResultPath = "",
    [string]$AccessLinkPlugin = "",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$FrameworkRoot = $PSScriptRoot
$HumanRoot = Split-Path $FrameworkRoot -Parent
$TestsRoot = Split-Path $HumanRoot -Parent
$RepositoryRoot = Split-Path $TestsRoot -Parent
$PlansRoot = Join-Path $HumanRoot "plans"
$FixturesRoot = Join-Path $HumanRoot "fixtures"
$LocalesRoot = Join-Path $HumanRoot "locales"
$DependenciesPath = Join-Path $HumanRoot "dependencies.json"
$ValidatorPath = Join-Path $FrameworkRoot "validate.py"
$TestInitPath = Join-Path $FrameworkRoot "init.lua"
$StateRoot = Join-Path $RepositoryRoot "tmp\human-test-state"
$ResultsRoot = Join-Path $RepositoryRoot "tmp\human-test-results"
$PythonRoot = Join-Path $StateRoot "python"
$PythonScripts = Join-Path $PythonRoot "Scripts"
$VenvPython = Join-Path $PythonScripts "python.exe"
$RuffPath = Join-Path $PythonScripts "ruff.exe"
$NodeRoot = Join-Path $StateRoot "node"
$NodeBin = Join-Path $NodeRoot "node_modules\.bin"
$PyrightRoot = Join-Path $NodeRoot "node_modules\pyright"
$PyrightPath = Join-Path $NodeBin "pyright-langserver.cmd"
$PackageRoot = Join-Path $StateRoot "packages"
$ManagedPluginsRoot = Join-Path $StateRoot "data\nvim-data\site\pack\core\opt"
$TestGitConfig = Join-Path $StateRoot "gitconfig"
$SetupMarker = Join-Path $StateRoot "setup.json"

if ([string]::IsNullOrWhiteSpace($AccessLinkPlugin)) {
    $AccessLinkPlugin = Join-Path $env:LOCALAPPDATA `
        "nvim-data\site\pack\nvim-nvda\start\nvim-nvda"
}
$AccessLinkPlugin = [IO.Path]::GetFullPath($AccessLinkPlugin)

if ($Language -eq "auto") {
    $detected = [Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName
    if ($detected -eq "de") {
        $Language = "de"
    } else {
        $Language = "en"
    }
}

$Messages = Get-Content -LiteralPath (Join-Path $LocalesRoot "$Language.json") `
    -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-Message {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [object[]]$Values = @()
    )
    $property = $script:Messages.PSObject.Properties[$Key]
    if ($null -eq $property) {
        throw "Missing locale key: $Key"
    }
    $template = [string]$property.Value
    if ($Values.Count -eq 0) {
        return $template
    }
    return [string]::Format(
        [Globalization.CultureInfo]::InvariantCulture,
        $template,
        $Values
    )
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-RequiredCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Hint
    )
    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $command) {
        throw (Get-Message "runner.requirementMissing" @($Name, $Hint))
    }
    return $command.Source
}

function Get-PythonInvocation {
    $launcher = Get-Command "py" -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $launcher) {
        $result = [PSCustomObject]@{
            Command = $launcher.Source
            Prefix = @("-3.12")
        }
    } else {
        $python = Get-Command "python" -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -eq $python) {
            throw (Get-Message "runner.requirementMissing" @(
                "Python 3.12",
                (Get-Message "runner.installPython")
            ))
        }
        $result = [PSCustomObject]@{
            Command = $python.Source
            Prefix = @()
        }
    }
    $versionArguments = @($result.Prefix) + @("--version")
    $versionResult = Invoke-ExternalText -Command $result.Command `
        -Arguments $versionArguments
    if ($versionResult.ExitCode -ne 0 -or
        $versionResult.Text -notmatch "^Python 3\.12\.") {
        throw (Get-Message "runner.requirementMissing" @(
            "Python 3.12",
            (Get-Message "runner.installPython")
        ))
    }
    return $result
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Arguments = @(),
        [int[]]$AcceptedExitCodes = @(0),
        [switch]$NoExitCode
    )
    $global:LASTEXITCODE = 0
    & $Command @Arguments
    $code = $LASTEXITCODE
    if ($AcceptedExitCodes -notcontains $code) {
        throw "$Command failed with exit code $code"
    }
    if (-not $NoExitCode) {
        return $code
    }
}

function Invoke-ExternalText {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Arguments = @()
    )
    # Windows PowerShell turns redirected native stderr into ErrorRecord
    # objects. With the runner's Stop preference, those records can otherwise
    # abort the script before LASTEXITCODE is inspected. Keep stderr captured
    # and let each caller decide whether the exit code is fatal.
    $previousErrorActionPreference = $ErrorActionPreference
    $nativePreference = Get-Variable -Name PSNativeCommandUseErrorActionPreference `
        -ErrorAction SilentlyContinue
    try {
        $ErrorActionPreference = "Continue"
        if ($null -ne $nativePreference) {
            Set-Variable -Name PSNativeCommandUseErrorActionPreference `
                -Value $false -Scope Local
        }
        $global:LASTEXITCODE = 0
        $output = @(& $Command @Arguments 2>&1)
        $code = $LASTEXITCODE
    } catch {
        $output = @($_)
        $code = -1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
        if ($null -ne $nativePreference) {
            Set-Variable -Name PSNativeCommandUseErrorActionPreference `
                -Value $nativePreference.Value -Scope Local
        }
    }
    $separator = [Environment]::NewLine
    $text = (($output | ForEach-Object { [string]$_ }) -join $separator).Trim()
    return [PSCustomObject]@{ ExitCode = [int]$code; Text = $text }
}

function Invoke-OptionalExternalText {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Arguments = @()
    )
    $result = Invoke-ExternalText -Command $Command -Arguments $Arguments
    if ($result.ExitCode -ne 0) {
        # Repository metadata is useful evidence but not a test prerequisite.
        # In particular, Windows cannot resolve a linked Linux worktree's
        # absolute gitdir path. Never expose Git's stderr or abort the run.
        return [PSCustomObject]@{ Succeeded = $false; Text = "" }
    }
    return [PSCustomObject]@{ Succeeded = $true; Text = $result.Text }
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [int[]]$AcceptedExitCodes = @(0)
    )
    $python = Get-PythonInvocation
    $combined = @($python.Prefix) + $Arguments
    return Invoke-External -Command $python.Command -Arguments $combined `
        -AcceptedExitCodes $AcceptedExitCodes
}

function Invoke-PythonText {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $python = Get-PythonInvocation
    $combined = @($python.Prefix) + $Arguments
    $result = Invoke-ExternalText -Command $python.Command -Arguments $combined
    if ($result.ExitCode -ne 0) {
        throw $result.Text
    }
    return $result.Text
}

function Install-PyrightPackage {
    param(
        [Parameter(Mandatory = $true)][string]$Npm,
        [Parameter(Mandatory = $true)][string]$Node,
        [Parameter(Mandatory = $true)][string]$Tar,
        [Parameter(Mandatory = $true)][object]$Dependencies
    )
    $version = [string]$Dependencies.tools.pyright
    $expectedSha512 = [string]$Dependencies.tools.pyrightSha512
    $packageJson = Join-Path $PyrightRoot "package.json"
    $langserver = Join-Path $PyrightRoot "langserver.index.js"
    $cli = Join-Path $PyrightRoot "index.js"
    $current = $false
    if ((Test-Path -LiteralPath $PyrightPath -PathType Leaf) -and
        (Test-Path -LiteralPath $packageJson -PathType Leaf) -and
        (Test-Path -LiteralPath $langserver -PathType Leaf) -and
        (Test-Path -LiteralPath $cli -PathType Leaf)) {
        try {
            $metadata = Get-Content -LiteralPath $packageJson -Raw -Encoding UTF8 |
                ConvertFrom-Json
            $current = [string]$metadata.version -eq $version
        } catch {
            $current = $false
        }
    }
    if ($current) {
        Write-Host (Get-Message "runner.setup.pyrightCurrent" @($version))
        $null = Invoke-External -Command $Node -Arguments @($cli, "--version")
        return
    }

    New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null
    $archive = Join-Path $PackageRoot "pyright-$version.tgz"
    $archiveValid = $false
    if (Test-Path -LiteralPath $archive -PathType Leaf) {
        $archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA512).Hash
        $archiveValid = $archiveHash.ToLowerInvariant() -eq $expectedSha512
        if (-not $archiveValid) {
            Remove-Item -LiteralPath $archive -Force
        }
    }
    if (-not $archiveValid) {
        Write-Step (Get-Message "runner.setup.pyrightArchive" @($version))
        $null = Invoke-External -Command $Npm -Arguments @(
            "pack", "--pack-destination", $PackageRoot, "--ignore-scripts",
            "--loglevel=info", "pyright@$version"
        )
    }
    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
        throw (Get-Message "runner.setup.pyrightArchiveMissing" @($archive))
    }
    $actualSha512 = (Get-FileHash -LiteralPath $archive -Algorithm SHA512).Hash.ToLowerInvariant()
    if ($actualSha512 -ne $expectedSha512) {
        throw (Get-Message "runner.setup.pyrightIntegrity" @($expectedSha512, $actualSha512))
    }

    Write-Step (Get-Message "runner.setup.pyrightExtract")
    $extractRoot = Join-Path $PackageRoot "pyright-extract"
    if (Test-Path -LiteralPath $extractRoot -PathType Container) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $PyrightRoot -PathType Container) {
        Remove-Item -LiteralPath $PyrightRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    New-Item -ItemType Directory -Path (Split-Path $PyrightRoot -Parent) -Force |
        Out-Null
    $null = Invoke-External -Command $Tar -Arguments @(
        "-xzf", $archive, "-C", $extractRoot
    )
    $extractedPackage = Join-Path $extractRoot "package"
    if (-not (Test-Path -LiteralPath $extractedPackage -PathType Container)) {
        throw (Get-Message "runner.setup.pyrightArchiveInvalid")
    }
    Move-Item -LiteralPath $extractedPackage -Destination $PyrightRoot
    Remove-Item -LiteralPath $extractRoot -Recurse -Force
    New-Item -ItemType Directory -Path $NodeBin -Force | Out-Null
    $shim = "@ECHO OFF`r`nnode `"%~dp0..\pyright\langserver.index.js`" %*`r`n"
    $ascii = New-Object Text.ASCIIEncoding
    [IO.File]::WriteAllText($PyrightPath, $shim, $ascii)
    $null = Invoke-External -Command $Node -Arguments @($cli, "--version")
}

function Get-EquivalentPaths {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullRoot = [IO.Path]::GetFullPath($Path)
    $roots = @($fullRoot.Replace("\", "/"))
    if ($fullRoot -match "^([A-Za-z]):[\\/](.*)$") {
        $driveName = $Matches[1]
        $relative = $Matches[2]
        $drive = Get-PSDrive -Name $driveName -ErrorAction SilentlyContinue
        if ($null -ne $drive) {
            $displayRootProperty = $drive.PSObject.Properties["DisplayRoot"]
            if ($null -ne $displayRootProperty -and
                -not [string]::IsNullOrWhiteSpace([string]$displayRootProperty.Value)) {
                $displayRoot = ([string]$displayRootProperty.Value).TrimEnd(
                    [char[]]@('\', '/')
                )
                $roots += "$displayRoot\$relative".Replace("\", "/")
            }
        }
    }
    return $roots
}

function Get-TestGitSafeDirectories {
    $names = @("nvim-lint", "nvim-cmp", "cmp-nvim-lsp", "blink.cmp")
    $directories = @(Get-EquivalentPaths -Path $RepositoryRoot)
    $roots = @(Get-EquivalentPaths -Path $ManagedPluginsRoot)
    foreach ($root in $roots) {
        foreach ($name in $names) {
            $directory = (Join-Path $root $name).Replace("\", "/")
            if ($directories -notcontains $directory) {
                $directories += $directory
            }
        }
    }
    return $directories
}

function Initialize-TestGitConfig {
    New-Item -ItemType Directory -Path (Split-Path $TestGitConfig -Parent) -Force |
        Out-Null
    $lines = @("[safe]")
    foreach ($safeDirectory in Get-TestGitSafeDirectories) {
        if ($safeDirectory.Contains('"')) {
            throw "Test Git safe directory contains an unsupported quote character"
        }
        $lines += "`tdirectory = `"$safeDirectory`""
    }
    $utf8 = New-Object Text.UTF8Encoding($false)
    $content = ($lines -join [Environment]::NewLine) + [Environment]::NewLine
    [IO.File]::WriteAllText($TestGitConfig, $content, $utf8)
}

function Assert-Definitions {
    Write-Step (Get-Message "runner.validating")
    $null = Invoke-Python @($ValidatorPath, "plans")
}

function Get-Plans {
    $plans = @(
        Get-ChildItem -LiteralPath $PlansRoot -Filter "*.json" -File |
            ForEach-Object {
                Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8 |
                    ConvertFrom-Json
            } |
            Sort-Object { [int]$_.order }
    )
    if ($Suite -eq "all") {
        return $plans
    }
    return @($plans | Where-Object { @($_.suites) -contains $Suite })
}

function Get-ResumableResultPaths {
    if (-not (Test-Path -LiteralPath $ResultsRoot -PathType Container)) {
        return @()
    }
    return @(
        Get-ChildItem -LiteralPath $ResultsRoot -Filter "*.json" -File |
            Sort-Object LastWriteTimeUtc -Descending |
            Where-Object {
                try {
                    $candidate = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8 |
                        ConvertFrom-Json
                    if ([int]$candidate.schemaVersion -ne 2) {
                        return $false
                    }
                    $statuses = @(
                        foreach ($plan in @($candidate.plans)) {
                            foreach ($step in @($plan.steps)) {
                                [string]$step.status
                            }
                        }
                    )
                    return ($statuses -contains "pending" -or
                        $statuses -contains "blocked" -or
                        $statuses -contains "skipped")
                } catch {
                    return $false
                }
            } |
            Select-Object -First 10
    )
}

function Select-ResumableResult {
    $candidates = @(Get-ResumableResultPaths)
    if ($candidates.Count -eq 0) {
        Write-Host (Get-Message "runner.resume.none") -ForegroundColor Yellow
        return ""
    }
    Write-Step (Get-Message "runner.resume.select")
    for ($index = 0; $index -lt $candidates.Count; $index += 1) {
        Write-Host "$($index + 1)  $($candidates[$index].Name)"
    }
    Write-Host "0  $(Get-Message 'runner.menu.exit')"
    while ($true) {
        $choice = Read-Host (Get-Message "runner.menu.prompt")
        if ($choice -eq "0") {
            return ""
        }
        $number = 0
        if ([int]::TryParse($choice, [ref]$number) -and
            $number -ge 1 -and $number -le $candidates.Count) {
            return $candidates[$number - 1].FullName
        }
        Write-Host (Get-Message "runner.invalidChoice") -ForegroundColor Yellow
    }
}

function Ask-Boolean {
    param(
        [Parameter(Mandatory = $true)][string]$Question,
        [bool]$Default
    )
    $defaultLabel = if ($Default) {
        Get-Message "runner.yes"
    } else {
        Get-Message "runner.no"
    }
    while ($true) {
        $answer = Read-Host "$Question $(Get-Message 'runner.yesNo' @($defaultLabel))"
        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $Default
        }
        $normalized = $answer.Trim().ToLowerInvariant()
        if (@("j", "ja", "y", "yes") -contains $normalized) {
            return $true
        }
        if (@("n", "nein", "no") -contains $normalized) {
            return $false
        }
    }
}

function Show-Menu {
    while ($true) {
        Write-Step (Get-Message "runner.title")
        Write-Host "1  $(Get-Message 'runner.menu.smoke')"
        Write-Host "2  $(Get-Message 'runner.menu.compatibility')"
        Write-Host "3  $(Get-Message 'runner.menu.all')"
        Write-Host "4  $(Get-Message 'runner.menu.resume')"
        Write-Host "5  $(Get-Message 'runner.menu.setup')"
        Write-Host "6  $(Get-Message 'runner.menu.list')"
        Write-Host "7  $(Get-Message 'runner.menu.verify')"
        Write-Host "8  $(Get-Message 'runner.menu.clean')"
        Write-Host "0  $(Get-Message 'runner.menu.exit')"
        $choice = Read-Host (Get-Message "runner.menu.prompt")
        switch ($choice) {
            "1" { $script:Action = "run"; $script:Suite = "smoke"; return $true }
            "2" { $script:Action = "run"; $script:Suite = "compatibility"; return $true }
            "3" { $script:Action = "run"; $script:Suite = "all"; return $true }
            "4" {
                $selected = Select-ResumableResult
                if (-not [string]::IsNullOrWhiteSpace($selected)) {
                    $script:Action = "run"
                    $script:ResultPath = $selected
                    return $true
                }
            }
            "5" { $script:Action = "setup"; return $true }
            "6" { $script:Action = "list"; return $true }
            "7" { $script:Action = "verify"; return $true }
            "8" { $script:Action = "clean"; return $true }
            "0" { return $false }
            default {
                Write-Host (Get-Message "runner.invalidChoice") -ForegroundColor Yellow
            }
        }
    }
}

function Get-Nvim {
    $nvim = Get-RequiredCommand "nvim" (Get-Message "runner.installNeovim")
    $global:LASTEXITCODE = 0
    $version = [string](& $nvim --version | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or $version.Trim() -notmatch "^NVIM v0\.12\.") {
        throw (Get-Message "runner.neovimVersion" @($version.Trim()))
    }
    return [PSCustomObject]@{
        Command = $nvim
        Version = $version.Trim()
    }
}

function Assert-AccessLinkPlugin {
    $entry = Join-Path $AccessLinkPlugin "plugin\nvim_nvda.lua"
    if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) {
        throw (Get-Message "runner.pluginMissing" @($AccessLinkPlugin))
    }
}

function Get-DefinitionFingerprint {
    return Invoke-PythonText @($ValidatorPath, "fingerprint")
}

function Get-PluginFingerprint {
    param([Parameter(Mandatory = $true)][string]$Path)
    return Invoke-PythonText @($ValidatorPath, "component-fingerprint", $Path)
}

function Assert-AccessLinkPluginCurrent {
    Assert-AccessLinkPlugin
    $expected = Get-PluginFingerprint (Join-Path $RepositoryRoot "neovim-plugin")
    $actual = Get-PluginFingerprint $AccessLinkPlugin
    if ($expected -ne $actual) {
        throw (Get-Message "runner.pluginMismatch" @($expected, $actual))
    }
    return $actual
}

function Invoke-TestNvim {
    param(
        [Parameter(Mandatory = $true)][string]$Profile,
        [string]$Fixture = "",
        [string]$Context = "",
        [string]$Task = "",
        [string]$Expected = "",
        [switch]$Headless,
        [switch]$Preflight,
        [switch]$ConfigurationDryRun
    )
    $nvim = Get-Nvim
    $environmentNames = @(
        "Path",
        "ACCESS_LINK_HUMAN_PROFILE",
        "ACCESS_LINK_HUMAN_PLUGIN",
        "ACCESS_LINK_HUMAN_DEPENDENCIES",
        "ACCESS_LINK_HUMAN_PYRIGHT",
        "ACCESS_LINK_HUMAN_RUFF",
        "ACCESS_LINK_HUMAN_DRY_RUN",
        "ACCESS_LINK_HUMAN_CONTEXT",
        "ACCESS_LINK_HUMAN_TASK",
        "ACCESS_LINK_HUMAN_EXPECTED",
        "ACCESS_LINK_HUMAN_LANGUAGE",
        "NVIM_NVDA_SESSION_NAME",
        "GIT_CONFIG_GLOBAL",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_CACHE_HOME"
    )
    $saved = @{}
    foreach ($name in $environmentNames) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    }
    try {
        $env:ACCESS_LINK_HUMAN_PROFILE = $Profile
        $env:ACCESS_LINK_HUMAN_PLUGIN = $AccessLinkPlugin
        $env:ACCESS_LINK_HUMAN_DEPENDENCIES = $DependenciesPath
        $env:ACCESS_LINK_HUMAN_PYRIGHT = $PyrightPath
        $env:ACCESS_LINK_HUMAN_RUFF = $RuffPath
        $env:ACCESS_LINK_HUMAN_DRY_RUN = if ($ConfigurationDryRun) { "1" } else { $null }
        $env:ACCESS_LINK_HUMAN_CONTEXT = $Context
        $env:ACCESS_LINK_HUMAN_TASK = $Task
        $env:ACCESS_LINK_HUMAN_EXPECTED = $Expected
        $env:ACCESS_LINK_HUMAN_LANGUAGE = $Language
        $env:NVIM_NVDA_SESSION_NAME = "Access Link human test: $Profile"
        $env:GIT_CONFIG_GLOBAL = $TestGitConfig
        $env:XDG_CONFIG_HOME = Join-Path $StateRoot "config"
        $env:XDG_DATA_HOME = Join-Path $StateRoot "data"
        $env:XDG_STATE_HOME = Join-Path $StateRoot "nvim-state"
        $env:XDG_CACHE_HOME = Join-Path $StateRoot "cache"
        $env:Path = "$PythonScripts;$NodeBin;$($saved['Path'])"
        foreach ($directory in @(
            $env:XDG_CONFIG_HOME,
            $env:XDG_DATA_HOME,
            $env:XDG_STATE_HOME,
            $env:XDG_CACHE_HOME
        )) {
            New-Item -ItemType Directory -Path $directory -Force | Out-Null
        }
        Initialize-TestGitConfig
        $arguments = @("-u", $TestInitPath, "-n", "-i", "NONE")
        if ($Headless) {
            $arguments += "--headless"
        }
        if (-not [string]::IsNullOrWhiteSpace($Fixture)) {
            $arguments += $Fixture
        }
        if ($Headless) {
            if ($Profile -eq "setup") {
                $arguments += "+lua if vim.g.access_link_human_setup_complete ~= 1 then vim.cmd('cquit 9') end"
            } elseif ($ConfigurationDryRun) {
                $arguments += "+lua if vim.g.access_link_human_config_ready ~= 1 then vim.cmd('cquit 9') end"
            } elseif ($Preflight) {
                $arguments += "+AccessLinkHumanPreflight"
                $arguments += "+lua if vim.g.access_link_human_preflight_ready ~= 1 then vim.cmd('cquit 9') end"
            } else {
                $arguments += "+lua if vim.g.access_link_human_config_ready ~= 1 or vim.fn.exists(':NvimNvdaSessionName') ~= 2 or vim.fn.exists(':NvimNvdaLspStatus') ~= 2 then vim.cmd('cquit 9') end"
            }
            $arguments += "+qa!"
        }
        Push-Location -LiteralPath $FixturesRoot
        try {
            if ($Headless) {
                $null = Invoke-External -Command $nvim.Command -Arguments $arguments
            } else {
                Invoke-External -Command $nvim.Command -Arguments $arguments -NoExitCode
            }
        } finally {
            Pop-Location
        }
    } finally {
        foreach ($name in $environmentNames) {
            [Environment]::SetEnvironmentVariable($name, $saved[$name], "Process")
        }
    }
}

function Test-SetupCurrent {
    if (-not (Test-Path -LiteralPath $SetupMarker -PathType Leaf) -or
        -not (Test-Path -LiteralPath $VenvPython -PathType Leaf) -or
        -not (Test-Path -LiteralPath $RuffPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $PyrightPath -PathType Leaf)) {
        return $false
    }
    try {
        $marker = Get-Content -LiteralPath $SetupMarker -Raw -Encoding UTF8 |
            ConvertFrom-Json
        $currentHash = (Get-FileHash -LiteralPath $DependenciesPath -Algorithm SHA256).Hash
        $definitionHash = Get-DefinitionFingerprint
        $pluginHash = Get-PluginFingerprint $AccessLinkPlugin
        return [string]$marker.dependenciesSha256 -eq $currentHash -and
            [string]$marker.definitionSha256 -eq $definitionHash -and
            [string]$marker.accessLinkPluginSha256 -eq $pluginHash
    } catch {
        return $false
    }
}

function Install-TestEnvironment {
    Write-Step (Get-Message "runner.setup.start")
    Write-Host (Get-Message "runner.setup.network")
    $null = Assert-AccessLinkPluginCurrent
    $null = Get-Nvim
    $null = Get-RequiredCommand "git" (Get-Message "runner.installGit")
    $npm = Get-RequiredCommand "npm" (Get-Message "runner.installNode")
    $node = Get-RequiredCommand "node" (Get-Message "runner.installNode")
    $tar = Get-RequiredCommand "tar" (Get-Message "runner.installTar")
    $python = Get-PythonInvocation
    $dependencies = Get-Content -LiteralPath $DependenciesPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    New-Item -ItemType Directory -Path $StateRoot -Force | Out-Null
    $currentHash = (Get-FileHash -LiteralPath $DependenciesPath -Algorithm SHA256).Hash
    if (Test-Path -LiteralPath $ManagedPluginsRoot -PathType Container) {
        Remove-Item -LiteralPath $ManagedPluginsRoot -Recurse -Force
    }
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        Write-Step (Get-Message "runner.setup.python")
        $arguments = @($python.Prefix) + @("-m", "venv", $PythonRoot)
        $null = Invoke-External -Command $python.Command -Arguments $arguments
    }
    Write-Step (Get-Message "runner.setup.ruff")
    $null = Invoke-External -Command $VenvPython -Arguments @(
        "-m", "pip", "install", "--disable-pip-version-check",
        "ruff==$($dependencies.tools.ruff)"
    )
    Write-Step (Get-Message "runner.setup.pyright")
    Install-PyrightPackage -Npm $npm -Node $node -Tar $tar `
        -Dependencies $dependencies
    Invoke-TestNvim -Profile "setup" -Headless
    foreach ($probe in @(
        [PSCustomObject]@{ Profile = "native"; Fixture = "lsp_features.py" },
        [PSCustomObject]@{ Profile = "diagnostics"; Fixture = "diagnostics.py" },
        [PSCustomObject]@{ Profile = "cmp"; Fixture = "lsp_features.py" },
        [PSCustomObject]@{ Profile = "blink"; Fixture = "lsp_features.py" }
    )) {
        Write-Step (Get-Message "runner.setup.preflight" @($probe.Profile))
        Invoke-TestNvim -Profile $probe.Profile `
            -Fixture (Join-Path $FixturesRoot $probe.Fixture) -Headless -Preflight
    }
    $marker = [PSCustomObject]@{
        schemaVersion = 2
        dependenciesSha256 = $currentHash
        definitionSha256 = Get-DefinitionFingerprint
        accessLinkPluginSha256 = Get-PluginFingerprint $AccessLinkPlugin
    }
    Write-JsonFile -Value $marker -Path $SetupMarker
    Write-Step (Get-Message "runner.setup.complete")
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)][object]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )
    $directory = Split-Path $Path -Parent
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $json = $Value | ConvertTo-Json -Depth 20
    $temporary = "$Path.new"
    $encoding = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, $encoding)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Get-RepositoryState {
    $commit = "unknown"
    $dirty = $true
    $git = Get-Command "git" -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $git) {
        Initialize-TestGitConfig
        $savedGitConfig = [Environment]::GetEnvironmentVariable(
            "GIT_CONFIG_GLOBAL", "Process"
        )
        try {
            $env:GIT_CONFIG_GLOBAL = $TestGitConfig
            $head = Invoke-OptionalExternalText -Command $git.Source -Arguments @(
                "-C", $RepositoryRoot, "rev-parse", "HEAD"
            )
            if ($head.Succeeded -and $head.Text -match "^[0-9a-f]{40}$") {
                $commit = $head.Text
            }
            $status = Invoke-OptionalExternalText -Command $git.Source -Arguments @(
                "-C", $RepositoryRoot, "status", "--porcelain=v1"
            )
            if ($status.Succeeded) {
                $dirty = -not [string]::IsNullOrWhiteSpace($status.Text)
            }
        } finally {
            [Environment]::SetEnvironmentVariable(
                "GIT_CONFIG_GLOBAL", $savedGitConfig, "Process"
            )
        }
    }
    return [PSCustomObject]@{
        commit = $commit
        dirty = $dirty
    }
}

function Get-CapabilityValue {
    param(
        [Parameter(Mandatory = $true)][object]$Capabilities,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $property = $Capabilities.PSObject.Properties[$Name]
    return $null -ne $property -and [bool]$property.Value
}

function Get-InstalledAddonVersion {
    $buildInfo = Join-Path $env:APPDATA `
        "nvda\addons\NeovimAccessLink\globalPlugins\NeovimAccessLink\build_info.py"
    if (-not (Test-Path -LiteralPath $buildInfo -PathType Leaf)) {
        return "unknown"
    }
    try {
        foreach ($line in Get-Content -LiteralPath $buildInfo -Encoding UTF8) {
            if ($line.TrimStart().StartsWith("ARTIFACT_VERSION")) {
                $parts = $line -split "=", 2
                if ($parts.Count -eq 2) {
                    $value = $parts[1].Trim().Trim([char]34).Trim([char]39)
                    if (-not [string]::IsNullOrWhiteSpace($value)) {
                        return $value
                    }
                }
            }
        }
    } catch {
        return "unknown"
    }
    return "unknown"
}

function Get-NvdaVersion {
    try {
        $process = Get-Process -Name "nvda" -ErrorAction Stop |
            Select-Object -First 1
        $version = [string]$process.MainModule.FileVersionInfo.ProductVersion
        if (-not [string]::IsNullOrWhiteSpace($version)) {
            return $version.Trim()
        }
    } catch {
        return "unknown"
    }
    return "unknown"
}

function New-Result {
    param(
        [Parameter(Mandatory = $true)][object[]]$Plans,
        [Parameter(Mandatory = $true)][object]$Capabilities
    )
    $nvim = Get-Nvim
    $pluginFingerprint = Assert-AccessLinkPluginCurrent
    $resultPlans = @()
    foreach ($plan in $Plans) {
        $resultSteps = @()
        foreach ($step in @($plan.steps)) {
            $missing = @(
                @($step.requires) | Where-Object {
                    -not (Get-CapabilityValue -Capabilities $Capabilities -Name $_)
                }
            )
            $status = if ($missing.Count -gt 0) { "notApplicable" } else { "pending" }
            $resultSteps += [PSCustomObject]@{
                id = [string]$step.id
                status = $status
                note = ""
            }
        }
        $resultPlans += [PSCustomObject]@{
            id = [string]$plan.id
            profile = [string]$plan.profile
            steps = $resultSteps
        }
    }
    return [PSCustomObject]@{
        schemaVersion = 2
        runId = [guid]::NewGuid().ToString()
        createdAt = [DateTimeOffset]::UtcNow.ToString("o")
        completedAt = ""
        repository = Get-RepositoryState
        environment = [PSCustomObject]@{
            language = $Language
            suite = $Suite
            neovimVersion = $nvim.Version
            audio = [bool]$Capabilities.audio
            braille = [bool]$Capabilities.braille
            definitionSha256 = Get-DefinitionFingerprint
            accessLinkPluginSha256 = $pluginFingerprint
            addonVersion = Get-InstalledAddonVersion
            nvdaVersion = Get-NvdaVersion
        }
        plans = $resultPlans
    }
}

function Show-Plans {
    param([Parameter(Mandatory = $true)][object[]]$Plans)
    Write-Step (Get-Message "runner.listHeader" @($Suite))
    $index = 0
    foreach ($plan in $Plans) {
        $index += 1
        Write-Host ""
        Write-Host (Get-Message "runner.card" @(
            $index,
            (Get-Message ([string]$plan.titleKey))
        )) -ForegroundColor Yellow
        Write-Host (Get-Message "runner.purpose" @(
            (Get-Message ([string]$plan.descriptionKey))
        ))
        foreach ($step in @($plan.steps)) {
            Write-Host "  $($step.id): $(Get-Message ([string]$step.titleKey))"
            Write-Host "    $(Get-Message 'runner.context'): $(Get-Message ([string]$step.contextKey))"
            Write-Host "    $(Get-Message 'runner.action'): $(Get-Message ([string]$step.actionKey))"
            Write-Host "    $(Get-Message 'runner.expected'): $(Get-Message ([string]$step.expectedKey))"
        }
    }
}

function Get-Outcome {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-Host ""
    Write-Host (Get-Message "runner.record" @($Title))
    Write-Host "1  $(Get-Message 'runner.record.pass')"
    Write-Host "2  $(Get-Message 'runner.record.fail')"
    Write-Host "3  $(Get-Message 'runner.record.blocked')"
    Write-Host "4  $(Get-Message 'runner.record.skipped')"
    while ($true) {
        $choice = Read-Host (Get-Message "runner.menu.prompt")
        $status = @{
            "1" = "pass"
            "2" = "fail"
            "3" = "blocked"
            "4" = "skipped"
        }[$choice]
        if (-not [string]::IsNullOrWhiteSpace($status)) {
            $note = ""
            if ($status -ne "pass") {
                while ([string]::IsNullOrWhiteSpace($note)) {
                    $note = Read-Host (Get-Message "runner.note")
                }
            }
            return [PSCustomObject]@{ status = $status; note = $note }
        }
    }
}

function Complete-ResultTimestamp {
    param([Parameter(Mandatory = $true)][object]$Result)
    $statuses = @(
        foreach ($plan in @($Result.plans)) {
            foreach ($step in @($plan.steps)) {
                [string]$step.status
            }
        }
    )
    if ($statuses -contains "pending" -or
        $statuses -contains "blocked" -or
        $statuses -contains "skipped") {
        $Result.completedAt = ""
    } else {
        $Result.completedAt = [DateTimeOffset]::UtcNow.ToString("o")
    }
}

function Invoke-ResultValidation {
    param([Parameter(Mandatory = $true)][string]$Path)
    $python = Get-PythonInvocation
    $arguments = @($python.Prefix) + @($ValidatorPath, "result", $Path)
    $global:LASTEXITCODE = 0
    & $python.Command @arguments | Out-Host
    $code = $LASTEXITCODE
    if (@(0, 2, 3) -notcontains $code) {
        throw "Result validation failed with exit code $code"
    }
    return [int]$code
}

function Run-Plans {
    $currentPluginFingerprint = Assert-AccessLinkPluginCurrent
    if (-not (Test-SetupCurrent)) {
        Write-Step (Get-Message "runner.setup.missing")
        Install-TestEnvironment
    }
    $plans = @(Get-Plans)
    $result = $null
    if (-not [string]::IsNullOrWhiteSpace($ResultPath) -and
        (Test-Path -LiteralPath $ResultPath -PathType Leaf)) {
        $null = Invoke-ResultValidation $ResultPath
        $result = Get-Content -LiteralPath $ResultPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        $script:Suite = [string]$result.environment.suite
        $script:Language = [string]$result.environment.language
        $script:Messages = Get-Content -LiteralPath `
            (Join-Path $LocalesRoot "$Language.json") -Raw -Encoding UTF8 |
            ConvertFrom-Json
        $plans = @(Get-Plans)
        Write-Step (Get-Message "runner.resume" @($ResultPath))
        if ([string]$result.environment.accessLinkPluginSha256 -ne
            $currentPluginFingerprint) {
            throw (Get-Message "runner.pluginMismatch" @(
                [string]$result.environment.accessLinkPluginSha256,
                $currentPluginFingerprint
            ))
        }
        $reopenable = @(
            foreach ($resultPlan in @($result.plans)) {
                foreach ($resultStep in @($resultPlan.steps)) {
                    if (@("blocked", "skipped") -contains [string]$resultStep.status) {
                        $resultStep
                    }
                }
            }
        )
        if ($reopenable.Count -gt 0 -and
            (Ask-Boolean (Get-Message "runner.resume.retry") $true)) {
            foreach ($resultStep in $reopenable) {
                $resultStep.status = "pending"
                $resultStep.note = ""
            }
            Complete-ResultTimestamp $result
            Write-JsonFile -Value $result -Path $ResultPath
            Write-Host (Get-Message "runner.resume.reopened" @($reopenable.Count))
        }
    } else {
        $capabilities = [PSCustomObject]@{
            audio = Ask-Boolean (Get-Message "runner.capability.audio") $true
            braille = Ask-Boolean (Get-Message "runner.capability.braille") $false
        }
        if ([string]::IsNullOrWhiteSpace($ResultPath)) {
            $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $suffix = [guid]::NewGuid().ToString("N").Substring(0, 8)
            $script:ResultPath = Join-Path $ResultsRoot "$timestamp-$Suite-$suffix.json"
        }
        $result = New-Result -Plans $plans -Capabilities $capabilities
        Write-JsonFile -Value $result -Path $ResultPath
    }

    try {
        $totalTasks = @(
            foreach ($resultPlan in @($result.plans)) {
                foreach ($resultStep in @($resultPlan.steps)) {
                    if ([string]$resultStep.status -eq "pending") {
                        $resultStep
                    }
                }
            }
        ).Count
        $taskIndex = 0
        $cardIndex = 0
        foreach ($plan in $plans) {
            $cardIndex += 1
            $resultPlan = @($result.plans | Where-Object { $_.id -eq $plan.id })[0]
            foreach ($step in @($plan.steps)) {
                $resultStep = @($resultPlan.steps | Where-Object { $_.id -eq $step.id })[0]
                if ($resultStep.status -eq "notApplicable") {
                    Write-Step (Get-Message "runner.card" @(
                        $cardIndex,
                        (Get-Message ([string]$plan.titleKey))
                    ))
                    Write-Host (Get-Message ([string]$step.titleKey)) -ForegroundColor Yellow
                    Write-Host (Get-Message "runner.notApplicable" @(
                        (@($step.requires) -join ", ")
                    ))
                    continue
                }
                if ($resultStep.status -ne "pending") {
                    continue
                }
                $taskIndex += 1
                $title = Get-Message ([string]$step.titleKey)
                $context = Get-Message ([string]$step.contextKey)
                $actionText = Get-Message ([string]$step.actionKey)
                $expectedText = Get-Message ([string]$step.expectedKey)
                Write-Step (Get-Message "runner.testProgress" @(
                    $taskIndex,
                    $totalTasks,
                    $title
                ))
                Write-Host (Get-Message "runner.card" @(
                    $cardIndex,
                    (Get-Message ([string]$plan.titleKey))
                )) -ForegroundColor Yellow
                Write-Host (Get-Message "runner.purpose" @(
                    (Get-Message ([string]$plan.descriptionKey))
                ))
                Write-Host ""
                Write-Host "$(Get-Message 'runner.context'): $context"
                Write-Host ""
                Write-Host "$(Get-Message 'runner.action'): $actionText"
                Write-Host ""
                Write-Host "$(Get-Message 'runner.expected'): $expectedText"
                Write-Host ""
                Write-Host (Get-Message "runner.orientation") -ForegroundColor Cyan
                Write-Host (Get-Message "runner.claimReminder")
                Write-Host (Get-Message "runner.controls")
                $null = Read-Host (Get-Message "runner.launchPrompt")
                $fixture = Join-Path $FixturesRoot ([string]$plan.fixture)
                Invoke-TestNvim -Profile ([string]$plan.profile) -Fixture $fixture `
                    -Context $context -Task $actionText -Expected $expectedText
                Write-Step (Get-Message "runner.afterReturn")
                Write-Host "$(Get-Message 'runner.expected'): $expectedText"
                $outcome = Get-Outcome $title
                $resultStep.status = $outcome.status
                $resultStep.note = $outcome.note
                Complete-ResultTimestamp $result
                Write-JsonFile -Value $result -Path $ResultPath
                Write-Host (Get-Message "runner.resultSaved" @($ResultPath))
            }
        }
    } finally {
        Complete-ResultTimestamp $result
        Write-JsonFile -Value $result -Path $ResultPath
    }
    Write-Step (Get-Message "runner.complete")
    $script:FinalExitCode = Invoke-ResultValidation $ResultPath
}

if ($Action -eq "menu") {
    if (-not (Show-Menu)) {
        return
    }
}

if ($Action -ne "clean") {
    Assert-Definitions
}

switch ($Action) {
    "setup" {
        Install-TestEnvironment
    }
    "list" {
        Show-Plans @(Get-Plans)
    }
    "verify" {
        if ([string]::IsNullOrWhiteSpace($ResultPath)) {
            $ResultPath = Read-Host (Get-Message "runner.verifyPrompt")
        }
        if (-not (Test-Path -LiteralPath $ResultPath -PathType Leaf)) {
            throw "Result file not found: $ResultPath"
        }
        $code = Invoke-ResultValidation $ResultPath
        exit $code
    }
    "clean" {
        if (Test-Path -LiteralPath $StateRoot -PathType Container) {
            if (Ask-Boolean (Get-Message "runner.clean.confirm") $false) {
                Remove-Item -LiteralPath $StateRoot -Recurse -Force
                Write-Step (Get-Message "runner.clean.complete")
            }
        }
    }
    "run" {
        if ($DryRun) {
            Show-Plans @(Get-Plans)
            $null = Assert-AccessLinkPluginCurrent
            foreach ($profile in @("native", "diagnostics", "cmp", "blink", "focus")) {
                Invoke-TestNvim -Profile $profile -Headless -ConfigurationDryRun
            }
            Write-Step (Get-Message "runner.dryRun")
        } else {
            $script:FinalExitCode = 1
            Run-Plans
            exit $script:FinalExitCode
        }
    }
}
