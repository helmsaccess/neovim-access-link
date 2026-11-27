# Guided Windows tests

The desktop group drives a disposable Windows guest through its QEMU virtual
keyboard. It checks Win32 foreground state, Windows Terminal UI Automation,
and NVDA speech and digital Braille. The audio group also records PCM and
checks the waveforms emitted during the guided actions.

```powershell
python tools/run_tests.py guided-desktop guided-audio --list
python tools/run_tests.py guided-desktop guided-audio --guided-config $labConfig --guided-addon $addon
python tools/run_tests.py guided-desktop --guided-config $labConfig --guided-addon $addon --guided-case P4
```

The two groups run only when requested. The runner executes cases serially
while it owns the guest. Use a different VM and QMP port for another suite.

## Prepare the isolated lab

Keep the guest disk, Windows and portable application archives, local tool
checkouts, guest sign-in setup and evidence in the auxiliary workspace.
Use a disposable Windows guest without networking. Its QEMU monitor must be
on loopback and expose the `payload` CD drive. The serial log must contain
the test bootstrap's `NAL_BOOT audit desktop ready` acknowledgement.
Use a QEMU build with `wavcapture` and the `capture` audio device for the
audio group. The existing auxiliary VM starter configures these devices.

Install the Windows test dependencies with
`python -m pip install -r tests/guided/windows/requirements.txt`.
Prepare the pinned tools in `tests/human/dependencies.json`.
The default Neovim and NVDA versions and portable archive names are in
`run_focus_test.py`. Use the official portable Windows Terminal distribution
for the `terminal-x64.zip` in the workspace.

For a fresh lab, run the focus driver once with the full software archives
and the packaged add-on. The driver expands the tools into a guest run
directory. Use the ID of that completed run as `reuseRun`. For a fresh
Windows installation that lacks the Visual C++ runtime, pass its signed
x64 redistributable with `--redistributable` on that first run.

```powershell
$env:NAL_TEST_WORK_DIR = $labWorkspace
$env:NAL_TEST_QMP_PORT = $qmpPort
python tests/guided/windows/run_focus_test.py $addon --nvda $nvdaArchive --nvim $nvimArchive --boot-timeout 720
python tests/guided/windows/prepare_audio_calibration.py .
```

Use the generated audio reference directory in the configuration. For C1–C3, D3 and D4,
build the WASAPI recorder from the pinned NAudio packages with
`build-wasapi-probe.ps1 -PackageDirectory $wasapiDirectory`.

## Local configuration

The JSON file uses `workspace`, `qmpPort`, `reuseRun` and `tools`. Paths can
be relative to the configuration file. Include only the tools needed for
the selected cases.

| Tools key | Expected input |
| --- | --- |
| `node`, `pyright` | Windows `node.exe` and the unpacked pinned Pyright package |
| `references`, `wasapi` | Generated WAV reference directory and built WASAPI recorder directory |
| `completionPlugins` | Parent of the pinned `nvimCmp`, `cmpNvimLsp` and `blinkCmp` checkouts |
| `providerGitBin`, `minGitBin` | Portable Git `ucrt64/bin` for the provider fixtures and full MinGit `cmd` for P1–P4 |
| `ruff`, `lint` | Pinned `ruff.exe` and nvim-lint checkout |
| `clangTidy`, `markdownModules` | Pinned `clang-tidy.exe` and markdownlint-cli2 `node_modules` |
| `lazy` | Pinned lazy.nvim checkout |

For an unattended restart, set `restart.launcher` to the local PowerShell
VM launcher and set `restart.disk` and `restart.bootMedia` to its existing
disk and ISO filenames. These files must be in the VM workspace. If the
guest uses a local sign-in profile, keep it with its matching bootstrap
media in the workspace. The restart guard checks QMP device identities and
the process before restarting a stopped guest.

## Read the results

The output directory contains `summary.json` and the audio proofs. Its case
entries identify the original `run-<ID>.json` and serial logs in the
workspace. A passing result requires executed steps, the expected package
hash and the matching cleanup acknowledgement. Where a case has a separate
control, the suite verifies both outcomes. Audio controls execute the
actions again with the feature tones disabled and must fail the normal cue
oracle. Physical Braille feel, acoustic perception and subjective latency
lie outside these digital measurements.

C1 requires both WASAPI and QEMU PCM evidence. C2, C3, D3 and D4 require
the WASAPI render endpoint. Their QEMU recordings and any rejected checks
are retained in the reports for diagnosis. D1 requires QEMU PCM evidence.
If C1 passes in the guest and the complete WASAPI recording but QEMU misses
only its start marker, the suite repeats that audio setting once. It archives
the rejected recording, report and source run. Both independent recordings
of the repeated run must satisfy the original checks.

```powershell
python tests/guided/windows/audit_result.py . $summary $addon $audioReferences --complete
```

The audit compares completed cases with their original serial logs, checks
the candidate hash, and reprocesses the PCM recordings. It compares the
recomputed audio measurements with the original reports and records the
SHA-256 of each verified waveform. For WASAPI it also checks the file size
and hash against the guest transfer. The audit rechecks the observed
Braille pages and editor cursor in L3, Quickfix results and edited
buffers against the source fixtures in L4–L6, all eleven diagnostics
actions and their recording markers in D1, the held and released Braille
frames in D2, and the effect of omitting F10 in S1. `--complete` returns
a failure if any of the 18 cases is missing, pending, or failed.

After a failure, preserve the original evidence and rerun the remaining
cards with `--guided-case`. Auditing both runs requires the same package
and VM workspace. Each card can have one passing result.

```powershell
python tests/guided/windows/audit_result.py . $summary $addon $audioReferences --additional-summary $continuation --complete
```

## Run the complete suite through GitHub Actions

Use a disposable Windows lab host associated only with a private caller
repository under the same owner. Give its runner the `nal-guided-vm` label.
Provision the same offline QEMU guest, pinned tools and reference audio as
for a local run. The desktop and WASAPI render endpoint belong to the guest.
On the lab host set `NAL_GUIDED_CI_CONFIG` to the absolute path of the
approved lab JSON and `NAL_GUIDED_CI_PYTHON` to the absolute path of the
Python executable with the pinned requirements installed. Provide the
normal Windows build tools and PowerShell 7 to the runner account. Keep
the VM files, raw evidence and guest credentials on the lab host.

Create this dispatcher on the default branch of the private lab repository
and substitute the reviewed 40-character commit SHA. Only the repository
owner can dispatch this job. Use a repository-scoped runner under a dedicated
standard Windows account, registered for a single job with `--ephemeral`.
The executor checks out that same revision to build the add-on and run its
tests. This workflow uses no GitHub-hosted runner or artifact uploads.

```yaml
name: Run the isolated Windows lab
on: workflow_dispatch
permissions:
  contents: read
jobs:
  lab:
    uses: helmsaccess/neovim-access-link/.github/workflows/guided-windows-vm.yml@REVIEWED_SHA
```

A passing lab job requires `audit_result.py --complete` to verify every
case against the built package. The GitHub job summary reports the source
commit and package hash. The local lab log and per-run directories hold
the diagnostic details. GitHub-hosted runner checks have separate job
names and report their directly observed behavior.
