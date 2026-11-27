"""Compare a real Windows Lazy action and its omitted-action control."""

import argparse
import json
from pathlib import Path


OPERATIONS = {"P2": "installation", "P3": "update", "P4": "synchronization"}


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def read_run(path, case):
    run = json.loads(path.read_text(encoding="utf-8"))
    require(run["ok"] is True and run["guestCleanupCompleted"] is True, "The guest run did not finish")
    prefix = case.lower()
    require(run["steps"][-2:] == [f"{prefix}_closed_lazy_and_returned_to_fixture", f"{prefix}_editor_exited_cleanly"],
            "Missing the return to the fixture or the clean editor exit")
    return run


def verify_expansion(positive, control):
    require(positive["expansionSkipped"] is False and control["expansionSkipped"] is True,
            "The expansion action and control must use different input sequences")
    require(positive["overview"] == control["overview"] and positive["rows"] == control["rows"],
            "The control changed the command bar or the collapsed plugin rows")
    for evidence in (positive, control):
        require(len(evidence["held"]) == 2 and evidence["openingContextCount"] in (0, 1),
                "Missing held navigation or duplicate Lazy window opening announcements")
    expanded, collapsed = positive["expansion"]
    untouched, = control["expansion"]
    require(expanded["expanded"] is True and expanded["speech"] == ["expanded"]
            and collapsed["expanded"] is False and collapsed["speech"] == ["collapsed"]
            and untouched["expanded"] is False and untouched["speech"] == []
            and expanded["cells"] != collapsed["cells"] == untouched["cells"] == positive["rows"][-1]["cells"],
            "The unchanged control must retain the collapsed Braille cells without announcing expansion")


def verify_operation(case, positive, control):
    require(all(run["case"] == case.lower() for run in (positive, control))
            and positive["operationSkipped"] is False and control["operationSkipped"] is True,
            "Wrong operation or omitted-action setting")
    before = positive["before"]
    expected = positive["expected"]
    clean_checkout = {name: {"revision": revision, "clean": True} if revision else None
                      for name, revision in expected.items()}
    require(set(before) == set(expected) and before == control["before"] == control["after"]
            and expected == control["expected"] and positive["after"] == clean_checkout != before,
            "Git snapshots did not preserve the identical starting state and show the expected change only once")
    operation = OPERATIONS[case]
    require(positive["operationSpeech"] == [f"lazy.nvim plugin manager: {operation} started",
            f"lazy.nvim plugin manager: {operation} finished; check the plugin manager for results"]
            and control["operationSpeech"] == [], "Incorrect NVDA lifecycle utterances")
    confirmed, = positive["verificationSpeech"]
    rejected, = control["verificationSpeech"]
    require(confirmed.startswith("Installed at the expected Git revision:")
            and rejected.startswith("Lazy test state is not complete yet:"), "F5 did not distinguish the Git states")


def compare(case, positive_path, control_path):
    positive = read_run(positive_path, case)
    control = read_run(control_path, case)
    require(positive["run"] != control["run"]
            and all(positive[key] == control[key] for key in ("candidate", "nvda", "terminal")),
            "The comparison needs separate runs of the same installed candidate")
    observed = (positive["lazyEvidence"], control["lazyEvidence"])
    if case == "P1":
        verify_expansion(*observed)
    else:
        verify_operation(case, *observed)
    return {"ok": True, "case": case, "positive": positive["run"], "control": control["run"],
            "candidate": positive["candidate"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("P1", *OPERATIONS))
    parser.add_argument("positive", type=Path)
    parser.add_argument("control", type=Path)
    arguments = parser.parse_args()
    try:
        result = compare(arguments.case, arguments.positive, arguments.control)
    except (KeyError, OSError, ValueError) as error:
        parser.exit(1, f"Lazy evidence pair rejected: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
