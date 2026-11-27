"""Assemble read-only media for a Windows audio render calibration."""

from array import array
import io
import math
from pathlib import Path
import sys
import uuid
import wave
from zipfile import ZipFile

import pycdlib

from lab_paths import SOURCES, WORKSPACE as ROOT


def marker(frequency: int, direction: int) -> bytes:
    output = io.BytesIO()
    frames = array("h", (
        int(12_000 * math.sin(math.pi * n / 19_200) ** 2
            * math.sin(2 * math.pi * (frequency * n / 48_000 + direction * 900 * (n / 48_000) ** 2)))
        for n in range(19_200)
    ))
    with wave.open(output, "wb") as stream:
        stream.setparams((1, 2, 48_000, 0, "NONE", "not compressed"))
        stream.writeframes(frames.tobytes())
    return output.getvalue()


def main(checkout: Path) -> None:
    run_id = f"audio-{uuid.uuid4().hex[:12]}"
    inputs = ROOT / run_id
    inputs.mkdir()
    sounds = checkout / "nvda-addon/addon/globalPlugins/NeovimAccessLink/resources/sounds"
    waves = {}
    with ZipFile(ROOT / "nvda-2026.3.1.zip") as nvda:
        waves["open"] = nvda.read("waves/suggestionsOpened.wav")
        waves["close"] = nvda.read("waves/suggestionsClosed.wav")
    for label in ("warning", "error", "none"):
        waves[label] = (sounds / f"diagnostic{label.capitalize()}.wav").read_bytes()
    waves["begin"] = marker(410, 1)
    waves["end"] = marker(2350, -1)
    waves["before-open"] = marker(1130, 1)
    waves["before-selection"] = marker(2960, 1)
    waves["before-accept"] = marker(4080, -1)
    waves["action"] = marker(5150, 1)
    iso = pycdlib.PyCdlib()
    try:
        iso.new(interchange_level=3, joliet=3, vol_ident="NALPAYLOAD")
        for index, (name, content) in enumerate(waves.items()):
            source = inputs / f"{name}.wav"
            source.write_bytes(content)
            iso.add_file(str(source), iso_path=f"/CUE{index}.WAV;1", joliet_path=f"/{name}.wav")
        token = inputs / "run-id.txt"
        token.write_text(run_id + "\n", encoding="ascii")
        iso.add_file(str(token), iso_path="/RUNID.TXT;1", joliet_path="/run-id.txt")
        iso.add_file(str(SOURCES / "guest-audio-calibration.ps1"), iso_path="/GUEST.PS1;1",
                     joliet_path="/guest-test.ps1")
        image = ROOT / f"{run_id}.iso"
        iso.write(str(image))
        print(image)
    finally:
        iso.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(strict=True))
