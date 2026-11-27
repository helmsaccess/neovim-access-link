"""Check identifiable PCM cues between separately rendered calibration markers."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import wave

import numpy as np


RATE = 24_000
CUES = ("open", "close", "warning", "error", "none")
C1_SEQUENCE = ("before-open", "open", "before-selection", "before-accept", "close")
MIN_CORRELATION = 0.85
MIN_RENDERED_RMS = 32
QUIET_WINDOW_RMS = 64


@dataclass(frozen=True)
class Match:
    cue: str
    start: int
    end: int
    correlation: float


def read_pcm(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as stream:
        if stream.getsampwidth() != 2:
            raise ValueError(f"{path} needs signed 16-bit PCM")
        rate = stream.getframerate()
        frames = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
        signal = frames.reshape(-1, stream.getnchannels()).mean(axis=1)
    if rate == RATE or not signal.size:
        return signal
    positions = np.arange(int(signal.size * RATE / rate)) * rate / RATE
    return np.interp(positions, np.arange(signal.size), signal)


def find_matches(recording: np.ndarray, template: np.ndarray, cue: str) -> list[Match]:
    width = len(template)
    if width > len(recording):
        return []
    template = template - template.mean()
    power = template @ template
    if power <= 0:
        raise ValueError(f"{cue} has no alternating PCM signal")
    size = 1 << (len(recording) + width - 2).bit_length()
    correlation = np.fft.irfft(
        np.fft.rfft(recording, size) * np.fft.rfft(template[::-1], size), size,
    )[width - 1:len(recording)]
    energy = np.concatenate(([0.0], np.cumsum(recording ** 2)))
    total = np.concatenate(([0.0], np.cumsum(recording)))
    variance = energy[width:] - energy[:-width] - (total[width:] - total[:-width]) ** 2 / width
    score = correlation / np.sqrt(power * np.maximum(variance, width * MIN_RENDERED_RMS ** 2))
    results = []
    while score.size:
        start = int(np.argmax(score))
        best = float(score[start])
        if best < MIN_CORRELATION:
            break
        results.append(Match(cue, start, start + width, best))
        score[max(0, start - width // 2):start + width // 2] = 0
    return results


def check_sequence(recording: np.ndarray, templates: dict[str, np.ndarray],
                   expected: tuple[str, ...]) -> list[Match]:
    markers = [find_matches(recording, templates[name], name) for name in ("begin", "end")]
    if any(len(matches) != 1 for matches in markers):
        raise ValueError(f"Expected one render marker at each end, found {[len(items) for items in markers]}")
    begin, end = (matches[0] for matches in markers)
    if end.start <= begin.end:
        raise ValueError("Render markers are out of order")

    interior = recording[begin.end:end.start]
    events = [
        Match(match.cue, match.start + begin.end, match.end + begin.end, match.correlation)
        for name, template in templates.items()
        if name not in {"begin", "end"}
        for match in find_matches(interior, template, name)
    ]
    selected = []
    for event in sorted(events, key=lambda item: item.correlation, reverse=True):
        overlaps = [
            other for other in selected
            if 2 * (min(other.end, event.end) - max(other.start, event.start))
            > min(event.end - event.start, other.end - other.start)
        ]
        if not overlaps:
            selected.append(event)
        elif any(other.cue != event.cue and other.correlation - event.correlation < 0.08
                 for other in overlaps):
            raise ValueError("Competing waveforms are too close to identify the rendered cue")
    events = selected
    events.sort(key=lambda match: match.start)
    sequence = tuple(match.cue for match in events)
    if sequence != expected:
        raise ValueError(f"Expected {expected}, found {sequence}")
    pairs = zip(events, events[1:])
    if any(left.end - RATE // 50 > right.start for left, right in pairs):
        raise ValueError("Cue matches overlap, so the sequence is ambiguous")
    return [begin, *events, end]


def check_negative_controls(recording: np.ndarray, templates: dict[str, np.ndarray],
                            expected: tuple[str, ...], found: list[Match]) -> list[str]:
    cues = [match for match in found if match.cue in CUES]
    if len(cues) < 2:
        raise ValueError("The negative controls need at least two rendered cues")
    begin = found[0]
    first = cues[0]
    second = next((cue for cue in cues[1:] if cue.cue != first.cue), None)
    reorder_control = "reordered cues"
    if second is None:
        second = next((event for event in found if event.cue == "action" and event.start > first.end), None)
        reorder_control = "cue moved across an action marker"
    if second is None:
        raise ValueError("Reordering needs two distinguishable rendered events")
    muted = recording.copy()
    muted[first.start:first.end] = 0
    duplicate = np.concatenate((
        recording[:first.end], np.zeros(RATE // 5),
        recording[first.start:first.end], recording[first.end:],
    ))
    reversed_pair = np.concatenate((
        recording[:first.start], recording[second.start:second.end],
        recording[first.end:second.start], recording[first.start:first.end],
        recording[second.end:],
    ))
    uncalibrated = recording.copy()
    uncalibrated[begin.start:begin.end] = 0
    controls = {
        "muted cue": (muted, "Expected ("),
        "duplicated cue": (duplicate, "Expected ("),
        reorder_control: (reversed_pair, "Expected ("),
        "missing render marker": (uncalibrated, "Expected one render marker"),
    }
    for name, (signal, reason) in controls.items():
        try:
            check_sequence(signal, templates, expected)
        except ValueError as error:
            if str(error).startswith(reason):
                continue
            raise ValueError(f"{name} failed at the wrong check: {error}") from error
        raise ValueError(f"The verifier accepted a recording with {name}")
    return list(controls)


def check_quiet_intervals(recording: np.ndarray, intervals: dict[str, tuple[int, int]]) -> dict:
    maximum_rms = {}
    for name, (start, end) in intervals.items():
        # Exclude only the immediate resampling margins of the two markers.
        margin = RATE // 100
        signal = recording[start + margin:max(start + margin, end - margin)]
        size = RATE // 50
        blocks = (signal[offset:offset + size] for offset in range(0, len(signal), size))
        maximum = max((float(np.sqrt(np.mean(block ** 2))) for block in blocks), default=0)
        if maximum > QUIET_WINDOW_RMS:
            raise ValueError(f"Unclassified audio {name}: peak 20 ms RMS {maximum:.1f}")
        maximum_rms[name] = {"rms": round(maximum, 3), "samples": len(signal)}
    return maximum_rms


def check_c1_quiet_intervals(recording: np.ndarray, matches: list[Match], *, muted: bool) -> dict:
    by_name = {match.cue: match for match in matches}
    intervals = {
        "before opening": (by_name["begin"].end, by_name["before-open"].start),
        "while selecting": (by_name["before-selection"].end, by_name["before-accept"].start),
    }
    if muted:
        intervals.update({
            "while opening": (by_name["before-open"].end, by_name["before-selection"].start),
            "while accepting": (by_name["before-accept"].end, by_name["end"].start),
        })
    return check_quiet_intervals(recording, intervals)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("references", type=Path)
    parser.add_argument("--expected", nargs="*", choices=CUES, default=CUES)
    parser.add_argument("--negative-controls", action="store_true")
    parser.add_argument("--c1-timeline", action="store_true")
    parser.add_argument("--c1-muted", action="store_true")
    parser.add_argument("--diagnostic-trace", "--d1-trace", dest="diagnostic_trace", type=Path)
    parser.add_argument("--diagnostics-muted", "--d1-muted", dest="diagnostics_muted", action="store_true")
    arguments = parser.parse_args()
    if arguments.c1_muted and (not arguments.c1_timeline or arguments.negative_controls):
        parser.error("The muted control needs the timeline without the waveform mutations")
    expected = C1_SEQUENCE if arguments.c1_timeline else tuple(arguments.expected)
    if arguments.diagnostic_trace:
        trace = json.loads(arguments.diagnostic_trace.read_text(encoding="utf-8"))
        actions = trace.get("diagnosticAudio", [])
        case = trace.get("diagnosticCase", "D1")
        keys = [action["key"] for action in actions]
        if case == "D1":
            valid = (len(actions) >= 2 and actions[0]["code"] == "F401"
                     and actions[-2]["code"] == "F821" and actions[-1]["cue"] == "none"
                     and {action["cue"] for action in actions} == {"warning", "error", "none"})
        elif case == "D3":
            valid = (keys == ["d1-current", "d1-next", "d1-next", "d1-previous"]
                     and all(item["code"] == "clang-diagnostic-error" and item["cue"] == "error"
                             for item in actions)
                     and actions[0]["row"] == actions[2]["row"] < actions[1]["row"] == actions[3]["row"])
        elif case == "D4":
            valid = (keys == ["d1-current", "d1-next"]
                     and all(item["code"] is None and "MD025" in item["message"]
                             and item["row"] == 3 and item["cue"] == "warning" for item in actions))
        else:
            valid = False
        if not (trace.get("ok") and valid):
            parser.error("Diagnostics audio requires the complete verified guest trace for the selected case")
        expected = tuple(
            name for action in actions for name in
            (("action",) if arguments.diagnostics_muted else ("action", action["cue"]))
        )
    if arguments.diagnostics_muted and (not arguments.diagnostic_trace or arguments.negative_controls):
        parser.error("The muted diagnostic control requires a trace without waveform mutations")
    if arguments.c1_muted:
        expected = tuple(name for name in expected if name not in CUES)
    names = tuple(dict.fromkeys(("begin", *CUES, *expected, "end")))
    templates = {
        name: read_pcm(arguments.references / f"{name}.wav")
        for name in names
    }
    try:
        recording = read_pcm(arguments.capture)
        matches = check_sequence(recording, templates, expected)
        quiet = check_c1_quiet_intervals(
            recording, matches, muted=arguments.c1_muted,
        ) if arguments.c1_timeline else {}
        if arguments.diagnostics_muted:
            quiet = check_quiet_intervals(recording, {
                f"action {i}": (start.end, end.start)
                for i, (start, end) in enumerate(zip(matches[1:], matches[2:]), start=1)
            })
        controls = check_negative_controls(recording, templates, expected, matches) if arguments.negative_controls else []
    except ValueError as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps({"matches": [
        {"cue": item.cue, "seconds": round(item.start / RATE, 4),
         "correlation": round(item.correlation, 4)}
        for item in matches
    ], "quietIntervalsPeakRms": quiet, "rejectedControls": controls}, indent=2))


if __name__ == "__main__":
    main()
