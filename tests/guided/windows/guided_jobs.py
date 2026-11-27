"""Select the Windows and PCM jobs for the guided test cards."""

from dataclasses import dataclass
import json
from pathlib import Path


DESKTOP = frozenset(("L1", "L2", "L3", "L4", "L5", "L6", "D2", "S1", "P1", "P2", "P3", "P4"))
AUDIO = frozenset(("C1", "C2", "C3", "D1", "D3", "D4"))
NATIVE_CONTROLS = {"L2": "--lsp-hints-disabled", "L4": "--l4-abort", "L6": "--lsp-missing-reference"}


@dataclass(frozen=True)
class Job:
    script: str
    arguments: tuple[str | Path, ...]
    muted: bool = False


def cards(checkout):
    plans = sorted(
        (json.loads(path.read_text(encoding="utf-8")) for path in (checkout / "tests/human/plans").glob("*.json")),
        key=lambda plan: plan["order"],
    )
    ids = tuple(step["testId"] for plan in plans for step in plan["steps"])
    if len(ids) != len(set(ids)) or set(ids) != DESKTOP | AUDIO:
        raise ValueError(f"The Windows test selection differs from the guided cards: {ids}")
    return ids


def jobs(case, *, addon, checkout, tools, output, reuse):
    focus = (addon, "--guided-root", checkout, "--reuse-run", reuse, "--boot-timeout", "720")
    audio = (addon, checkout)
    if case in ("L1", "L2", "L3", "L5", "D2"):
        focus += ("--c1-node", tools["node"], "--c1-pyright", tools["pyright"])
    if case == "S1":
        return (Job("run_focus_test.py", (*focus, "--s1-with-control")),)
    if case == "L3":
        return (Job("run_focus_test.py", (*focus, "--l3-held", "--l3-with-control")),)
    if case == "D2":
        return (Job("run_focus_test.py", (*focus, "--c1-markers", tools["references"],
                    "--d1-ruff", tools["ruff"], "--d1-lint", tools["lint"],
                    "--d1-git-bin", tools["providerGitBin"], "--d2-held")),)
    if case.startswith("P") and case in DESKTOP:
        arguments = (*focus, "--lazy-case", case, "--lazy-checkout", tools["lazy"], "--lazy-git-bin", tools["minGitBin"])
        return (Job("run_focus_test.py", arguments), Job("run_focus_test.py", (*arguments, "--lazy-skip-operation")))
    if case in DESKTOP:
        arguments = (*focus, "--native-lsp", case)
        result = (Job("run_focus_test.py", arguments),)
        if control := NATIVE_CONTROLS.get(case):
            result += (Job("run_focus_test.py", (*arguments, control)),)
        return result

    if case not in AUDIO:
        raise ValueError(f"Unknown guided case: {case}")
    if case.startswith("C"):
        script = "run_c1_audio.py"
        arguments = (*audio, tools["node"], tools["pyright"], tools["references"])
        options = ("--wasapi-tools", tools["wasapi"])
        if case != "C1":
            options += ("--completion-profile", {"C2": "cmp", "C3": "blink"}[case],
                        "--completion-plugins", tools["completionPlugins"],
                        "--completion-git-bin", tools["providerGitBin"])
    elif case == "D1":
        script = "run_d1_audio.py"
        arguments = (*audio, tools["node"], tools["pyright"], tools["ruff"],
                     tools["lint"], tools["providerGitBin"], tools["references"])
        options = ()
    else:
        script = "run_external_diagnostic_audio.py"
        linter = tools["clangTidy"] if case == "D3" else tools["markdownModules"]
        arguments = (case, *audio, linter, tools["lint"], tools["providerGitBin"], tools["references"])
        options = ("--wasapi-tools", tools["wasapi"])
        if case == "D4":
            options += ("--node", tools["node"])
    common = (*options, "--reuse-run", reuse)
    return (
        Job(script, (*arguments, output / f"{case}-positive.wav", *common)),
        Job(script, (*arguments, output / f"{case}-muted.wav", *common, "--muted"), muted=True),
    )
