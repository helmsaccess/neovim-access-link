# Run the guided suite from a reviewed checkout on the dedicated Windows lab runner.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows' -or
    $env:NAL_GUIDED_CI_SOURCE_SHA -cnotmatch '^[a-f0-9]{40}$' -or
    $env:GITHUB_RUN_ID -cnotmatch '^[0-9]+$' -or $env:GITHUB_RUN_ATTEMPT -cnotmatch '^[0-9]+$') {
    throw 'The guided lab entry point requires an identified Windows Actions job.'
}
if (!$env:NAL_GUIDED_CI_CONFIG -or !$env:NAL_GUIDED_CI_PYTHON -or
    ![IO.Path]::IsPathFullyQualified($env:NAL_GUIDED_CI_CONFIG) -or
    ![IO.Path]::IsPathFullyQualified($env:NAL_GUIDED_CI_PYTHON) -or
    !(Test-Path -LiteralPath $env:NAL_GUIDED_CI_CONFIG -PathType Leaf) -or
    !(Test-Path -LiteralPath $env:NAL_GUIDED_CI_PYTHON -PathType Leaf)) {
    throw 'The runner must provide its approved lab configuration and Python executable.'
}

$labLog = $null
$phase = 'lab configuration'
try {
    $config = Get-Item -LiteralPath $env:NAL_GUIDED_CI_CONFIG
    $settings = Get-Content -LiteralPath $config.FullName -Raw | ConvertFrom-Json
    $workspace = Get-Item -LiteralPath ([IO.Path]::GetFullPath($settings.workspace, $config.DirectoryName))
    $references = Get-Item -LiteralPath ([IO.Path]::GetFullPath($settings.tools.references, $config.DirectoryName))
    if (!$workspace.PSIsContainer -or !$references.PSIsContainer -or !$settings.restart) {
        throw 'A provisioned workspace, audio references and isolated guest restart settings are required.'
    }
    $jobId = "$env:GITHUB_RUN_ID-$env:GITHUB_RUN_ATTEMPT"
    $log = Join-Path $workspace.FullName "guided-ci-$jobId.log"
    New-Item -ItemType File -Path $log | Out-Null
    $labLog = $log

    $phase = 'source revision'
    $source = & git rev-parse --verify HEAD 2>> $log
    if ($LASTEXITCODE -ne 0 -or $source -cne $env:NAL_GUIDED_CI_SOURCE_SHA) {
        throw 'The checkout does not match the reviewed workflow commit.'
    }
    & git switch --create "codex/ci-$jobId" >> $log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the clean local development branch.' }

    $phase = 'development package build'
    $python = $env:NAL_GUIDED_CI_PYTHON
    & $env:ComSpec /d /c 'build.cmd < NUL' >> $log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'The development build failed.' }
    $addonName = & $python -c 'import buildVars; print(buildVars.addon_info["name"] + "-" + buildVars.artifact_version() + ".nvda-addon")' 2>> $log
    if ($LASTEXITCODE -ne 0 -or !$addonName -or [IO.Path]::GetFileName($addonName) -cne $addonName) {
        throw 'The exact development package name could not be resolved.'
    }
    $addon = Get-Item -LiteralPath (Join-Path 'dist' $addonName)
    if ($addon.PSIsContainer) { throw 'The development package must be a file.' }
    $digest = (Get-FileHash -LiteralPath $addon.FullName -Algorithm SHA256).Hash.ToLowerInvariant()

    $phase = 'PCM calibration controls'
    & $python tests/guided/windows/test_c1_calibration.py >> $log 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'The QEMU calibration controls failed.' }

    $phase = 'Windows VM suite'
    $env:NAL_TEST_STOP_GUEST_AFTER_SUITE = '1'
    $env:NAL_TEST_CONTINUE_GUIDED_CASES = '1'
    $filter = 'guided-suite-*'
    $previous = @(Get-ChildItem -LiteralPath $workspace.FullName -Directory -Filter $filter | Select-Object -ExpandProperty Name)
    & $python tools/run_tests.py guided-desktop guided-audio --guided-config $config.FullName --guided-addon $addon.FullName >> $log 2>&1
    $suiteExit = $LASTEXITCODE
    $outputs = @(Get-ChildItem -LiteralPath $workspace.FullName -Directory -Filter $filter |
        Where-Object { $_.Name -cmatch '^guided-suite-[a-f0-9]{12}$' -and $_.Name -notin $previous })
    if ($outputs.Count -ne 1) { throw 'The suite did not produce one new evidence directory.' }
    $summary = Join-Path $outputs[0].FullName 'summary.json'

    $phase = 'complete evidence audit'
    $raw = & $python tests/guided/windows/audit_result.py . $summary $addon.FullName $references.FullName --complete 2>> $log
    $auditExit = $LASTEXITCODE
    $raw | Add-Content -LiteralPath $log
    if ($raw) {
        $audit = ($raw -join "`n") | ConvertFrom-Json
        $cases = @($audit.cases.PSObject.Properties)
        $passedCount = @($cases | Where-Object { $_.Value.status -ceq 'verified' }).Count
        "Rechecked $passedCount of $($cases.Count) guided Windows VM cases." | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
    }
    if ($auditExit -ne 0) { throw 'The complete evidence audit failed.' }
    if ($suiteExit -ne 0 -or $audit.complete -ne $true -or $audit.candidate.sha256 -cne $digest -or
        !$cases.Count -or @($cases | Where-Object { $_.Value.status -cne 'verified' }).Count) {
        throw 'The evidence audit did not verify every case against the expected package.'
    }
    $verified = "Verified $($cases.Count) guided Windows VM cases for $source (add-on SHA-256: $digest)."
    Write-Output $verified
    $verified | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
} catch {
    if ($labLog) { ($_ | Out-String) | Add-Content -LiteralPath $labLog }
    throw "Guided Windows VM job failed during $phase. Inspect the dedicated runner's local lab log."
}
