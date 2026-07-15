from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time

from .bridge import Bridge
from .session_registry import discover_session, list_sessions


def main() -> int:
    parser = argparse.ArgumentParser(description="Neovim NVDA Linux bridge")
    parser.add_argument("--nvim-socket", help="Neovim RPC socket; auto-discovered when omitted")
    parser.add_argument("--session", help="registered Neovim session id or unique name")
    parser.add_argument("--list-sessions", action="store_true", help="list registered sessions as JSON and exit")
    args = parser.parse_args()
    if args.list_sessions:
        print(json.dumps([
            {"id": session.identifier, "name": session.name, "cwd": session.cwd,
             "pid": session.pid, "startedUnix": session.started_unix,
             "claimSequence": session.claim_sequence,
             "claimAgeMs": (
                 max(0, (time.monotonic_ns() - session.claimed_monotonic) // 1_000_000)
                 if session.claimed_monotonic else -1
             )}
            for session in list_sessions()
        ], ensure_ascii=False))
        return 0
    session_nonce = None
    if not args.nvim_socket:
        try:
            session = discover_session(selector=args.session or "")
            args.nvim_socket = session.socket
            session_nonce = session.session_nonce
        except RuntimeError as error:
            parser.error(str(error))
    bridge = Bridge(
        args.nvim_socket, stdio_streams=(sys.stdin.buffer, sys.stdout.buffer),
        session_nonce=session_nonce,
    )
    stopped = threading.Event()

    def stop(_signum=None, _frame=None) -> None:
        stopped.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    bridge.start()
    try:
        while not stopped.wait(0.1):
            closed = bridge.transport.closed
            if closed is not None and closed.is_set():
                break
    finally:
        bridge.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
