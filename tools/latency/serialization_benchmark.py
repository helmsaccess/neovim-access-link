#!/usr/bin/env python3
"""Compare serialization cost and size for a representative state event."""

from __future__ import annotations

import json
import statistics
import time

import msgpack

EVENT = {
    "protocolVersion": 2,
    "sessionId": "7b991087-8a65-41f0-a346-35ae43d72e56",
    "sequence": 123,
    "timestampMonotonic": 123456789,
    "type": "cursorMoved",
    "payload": {
        "mode": "normal",
        "modeRaw": "n",
        "bufferId": 1,
        "windowId": 1000,
        "cursor": {"line": 10, "byteColumn": 7, "characterColumn": 6, "virtualColumn": 8},
        "lineText": "tab\tcombining é wide 界 emoji 🙂",
        "changedtick": 42,
    },
}


def measure(name: str, encode, decode, count: int = 100_000) -> None:
    encoded = encode(EVENT)
    encode_samples: list[int] = []
    decode_samples: list[int] = []
    for _ in range(count):
        start = time.perf_counter_ns()
        data = encode(EVENT)
        encode_samples.append(time.perf_counter_ns() - start)
        start = time.perf_counter_ns()
        decode(data)
        decode_samples.append(time.perf_counter_ns() - start)
    print(
        f"{name} n={count} bytes={len(encoded)} "
        f"encode_median_us={statistics.median(encode_samples) / 1000:.2f} "
        f"decode_median_us={statistics.median(decode_samples) / 1000:.2f}"
    )


measure(
    "msgpack",
    lambda value: msgpack.packb(value, use_bin_type=True),
    lambda value: msgpack.unpackb(value, raw=False),
)
measure(
    "json",
    lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(),
    lambda value: json.loads(value),
)
