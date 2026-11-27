param(
    [Parameter(Mandatory)][ValidateSet('P1', 'P2', 'P3', 'P4')][string]$Case,
    [Parameter(Mandatory)][string]$Root,
    [Parameter(Mandatory)][string]$Seeds,
    [Parameter(Mandatory)][string]$Git
)

$ErrorActionPreference = 'Stop'
function Invoke-FixtureGit {
    $output = & $Git @args
    if ($LASTEXITCODE -ne 0) { throw "Fixture Git failed with exit code ${LASTEXITCODE}: $args" }
    return $output
}

New-Item -ItemType Directory -Path $Root | Out-Null
$env:GIT_TEMPLATE_DIR = (New-Item -ItemType Directory -Path (Join-Path $Root 'git-template')).FullName
$source = Join-Path $Root 'source'
$origins = (New-Item -ItemType Directory -Path (Join-Path $Root 'origins')).FullName
$plugins = (New-Item -ItemType Directory -Path (Join-Path $Root 'plugins')).FullName
$null = Invoke-FixtureGit init --quiet --initial-branch=main $source
$null = Invoke-FixtureGit -C $source config core.autocrlf false
$pluginFile = Join-Path (New-Item -ItemType Directory -Path (Join-Path $source 'plugin')).FullName 'access_link_lazy_fixture.lua'
$revisions = @{}
$dates = @{ a = '2000-01-01T00:00:00+00:00'; b = '2000-01-02T00:00:00+00:00' }
$previousAuthorDate = $env:GIT_AUTHOR_DATE
$previousCommitterDate = $env:GIT_COMMITTER_DATE
try {
    foreach ($label in @('a', 'b')) {
        $env:GIT_AUTHOR_DATE = $dates[$label]
        $env:GIT_COMMITTER_DATE = $dates[$label]
        [IO.File]::WriteAllBytes($pluginFile, [IO.File]::ReadAllBytes((Join-Path $Seeds "lazy-plugin-$label.lua")))
        $null = Invoke-FixtureGit -C $source add plugin/access_link_lazy_fixture.lua
        $null = Invoke-FixtureGit -C $source -c 'user.name=Access Link Test' -c 'user.email=human-test.invalid' -c commit.gpgSign=false commit --quiet -m "Fixture $label"
        $revisions[$label] = (Invoke-FixtureGit -C $source rev-parse HEAD).Trim()
        if ($revisions[$label] -notmatch '^[0-9a-f]{40}$') { throw 'Invalid fixture revision' }
    }
} finally {
    $env:GIT_AUTHOR_DATE = $previousAuthorDate
    $env:GIT_COMMITTER_DATE = $previousCommitterDate
}

$start = switch ($Case) {
    'P1' { @{ stable = 'b'; update = 'b' } }
    'P2' { @{ install = $null } }
    'P3' { @{ update = 'a' } }
    'P4' { @{ install = $null; update = 'a'; stale = 'b' } }
}
$operation = @{ P1 = 'window'; P2 = 'install'; P3 = 'update'; P4 = 'sync' }[$Case]
$entries = [System.Collections.Generic.List[object]]::new()
$absent = [System.Collections.Generic.List[string]]::new()
$initial = @{}
foreach ($role in ($start.Keys | Sort-Object)) {
    $name = "access-link-$role-target"
    $origin = Join-Path $origins "$name.git"
    $directory = Join-Path $plugins $name
    $null = Invoke-FixtureGit clone --quiet --bare --no-hardlinks $source $origin
    $revision = $null
    if ($start[$role]) { $revision = $revisions[$start[$role]] }
    $initial[$name] = $revision
    if ($revision) {
        $null = Invoke-FixtureGit clone --quiet --no-hardlinks $origin $directory
        if ($revision -ne $revisions.b) {
            $null = Invoke-FixtureGit -C $directory -c advice.detachedHead=false checkout --quiet --detach $revision
        }
    }
    if ($role -eq 'stale') {
        $absent.Add($directory)
    } else {
        $entries.Add(@{ name = $name; url = $origin; expectedRevision = $revisions.b })
    }
}
$metadata = @{
    schemaVersion = 1; operation = $operation; root = $plugins
    lockfile = Join-Path $Root 'lazy-lock.json'
    plugins = @($entries.ToArray()); absent = @($absent.ToArray()); initial = $initial
}
$file = Join-Path $Root 'fixture.json'
[IO.File]::WriteAllText($file, ($metadata | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
Write-Output $file
