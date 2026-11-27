"""Recover an isolated guest's sign-in screen after setup auto-logons expire."""
from contextlib import suppress
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import string
import time
import uuid
import xml.etree.ElementTree as ET

import pycdlib

from qmp import Qmp


PUNCTUATION = {
    "-": "minus", "=": "equal", ",": "comma", ".": "dot", "/": "slash",
    "[": "bracket_left", "]": "bracket_right", ";": "semicolon", "'": "apostrophe", " ": "spc",
}
SHIFTED = dict(zip("!@#$%^&*()_+<>?:{}", "1234567890-=,./;[]"))


def keys(character):
    if character in string.ascii_lowercase + string.digits:
        return (character,)
    if character in string.ascii_uppercase:
        return "shift", character.lower()
    if character in PUNCTUATION:
        return (PUNCTUATION[character],)
    if character in SHIFTED:
        return ("shift", *keys(SHIFTED[character]))
    raise ValueError("The test credential needs a key unsupported by the configured layout")


def credential_keys(boot_media, account):
    xml = BytesIO()
    disc = pycdlib.PyCdlib()
    disc.open(str(boot_media))
    try:
        disc.get_file_from_iso_fp(xml, joliet_path="/Autounattend.xml")
    finally:
        disc.close()
    ns = {"u": "urn:schemas-microsoft-com:unattend"}
    entry, = [item for item in ET.fromstring(xml.getvalue()).findall(".//u:AutoLogon", ns)
              if item.findtext("u:Username", namespaces=ns) == account]
    credential = entry.findtext("u:Password/u:Value", namespaces=ns)
    if not credential or entry.findtext("u:Password/u:PlainText", namespaces=ns) != "true":
        raise ValueError("The trusted test bootstrap lacks its configured sign-in credential")
    return [keys(character) for character in credential]


def screenshot_data(path, size):
    width, height = size
    with path.open("rb") as stream:
        if [stream.readline().strip() for _ in range(3)] != [
            b"P6", f"{width} {height}".encode("ascii"), b"255",
        ]:
            return None
        data = stream.read(width * height * 3 + 1)
    return data if len(data) == width * height * 3 else None


def crop_sha256(screen, size, boxes):
    width, height = size
    digest = sha256()
    for x, y, right, bottom in boxes:
        if not (0 <= x < right <= width and 0 <= y < bottom <= height):
            raise ValueError("Invalid sign-in image rectangle")
        for row in range(y, bottom):
            digest.update(screen[3 * (row * width + x):3 * (row * width + right)])
    return digest.hexdigest()


def enter_credential(guest, sequence):
    active = []
    try:
        for group in sequence:
            if len(group) == 2:
                guest.key_transition("shift", down=True)
                active.append("shift")
                time.sleep(0.20)
            guest.key_transition(group[-1], down=True)
            active.append(group[-1])
            time.sleep(0.11)
            guest.key_transition(group[-1], down=False)
            active.pop()
            if len(group) == 2:
                time.sleep(0.11)
                guest.key_transition("shift", down=False)
                active.pop()
            time.sleep(0.30)
        guest.key("ret")
    except (EOFError, OSError, RuntimeError):
        raise RuntimeError("QEMU did not complete the isolated test-account sign-in") from None
    finally:
        for key in reversed(active):
            with suppress(EOFError, OSError, RuntimeError):
                guest.key_transition(key, down=False)


class GuestSignIn:
    def __init__(self, profile_path):
        self.root = profile_path.parent.resolve()
        self.profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
        self.disk = (self.root / self.profile["disk"]).resolve(strict=True)
        self.boot_media = (self.root / self.profile["bootMedia"]).resolve(strict=True)
        if self.disk.parent != self.root or self.boot_media.parent != self.root:
            raise ValueError("The sign-in profile must use media in the test VM directory")
        self.woke = False
        self.submitted = False

    def observe(self):
        if self.submitted:
            return
        with Qmp() as guest:
            images = {Path(item["inserted"]["file"]).resolve() for item in guest.execute("query-block")
                      if item.get("inserted") and item["inserted"].get("file")}
            if not {self.disk, self.boot_media} <= images:
                return
            probe = self.root / f"guest-signin-{uuid.uuid4().hex}.ppm"
            try:
                guest.execute("screendump", filename=probe.as_posix(), format="ppm")
                screen = screenshot_data(probe, self.profile["size"])
            finally:
                probe.unlink(missing_ok=True)
            if screen is None:
                return
            for name in ("password", "lock"):
                state = self.profile[name]
                if crop_sha256(screen, self.profile["size"], state["boxes"]) != state["sha256"]:
                    continue
                if name == "lock" and not self.woke:
                    guest.key("ret")
                    self.woke = True
                if name == "password":
                    sequence = credential_keys(self.boot_media, self.profile["account"])
                    self.submitted = True
                    enter_credential(guest, sequence)
                    print("Submitted sign-in for the isolated test account.", flush=True)
                return
