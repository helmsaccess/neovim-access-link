"""Drive only the local test VM's QEMU monitor."""
import json
import os
from pathlib import Path
import socket
import sys

from lab_paths import WORKSPACE

PORT = int(os.environ.get("NAL_TEST_QMP_PORT", "31946"))


class Qmp:
    def __init__(self, port=PORT):
        self.port = port

    def __enter__(self):
        self.connection = socket.create_connection(("127.0.0.1", self.port), timeout=12)
        self.stream = self.connection.makefile("rwb")
        greeting = json.loads(self.stream.readline())
        if "QMP" not in greeting:
            raise RuntimeError(greeting)
        self.execute("qmp_capabilities")
        return self

    def __exit__(self, *_):
        self.stream.close()
        self.connection.close()

    def execute(self, command, **arguments):
        request = {"execute": command}
        if arguments:
            request["arguments"] = arguments
        self.stream.write(json.dumps(request).encode("utf-8") + b"\n")
        self.stream.flush()
        while message := self.stream.readline():
            reply = json.loads(message)
            if "error" in reply:
                raise RuntimeError(reply["error"])
            if "return" in reply:
                return reply["return"]
        raise EOFError(command)

    def key(self, *codes):
        return self.execute("send-key", keys=[{"type": "qcode", "data": code} for code in codes],
                            **{"hold-time": 90})

    def key_transition(self, code, *, down):
        return self.execute("input-send-event", events=[{
            "type": "key", "data": {"down": down, "key": {"type": "qcode", "data": code}},
        }])


if __name__ == "__main__":
    with Qmp() as qmp:
        action = sys.argv[1]
        if action == "screen":
            print(qmp.execute("screendump", filename=str(Path(sys.argv[2]).resolve()), format="png"))
        elif action == "mount":
            path = Path(sys.argv[2]).resolve(strict=True)
            if path.parent != WORKSPACE or path.suffix != ".iso":
                raise ValueError("Test media must be an ISO in the test VM directory")
            print(qmp.execute("blockdev-change-medium", device="payload", filename=path.as_posix(),
                              format="raw", **{"read-only-mode": "read-only"}))
        elif action == "key":
            print(qmp.key(*sys.argv[2:]))
        else:
            print(qmp.execute(action))
