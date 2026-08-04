#!/usr/bin/env python3
"""Small deterministic stdio LSP server for real Neovim contract tests."""

from __future__ import annotations

import json
import sys
from typing import Any


def read_message() -> dict[str, Any] | None:
	content_length = None
	while True:
		line = sys.stdin.buffer.readline()
		if not line:
			return None
		if line in {b"\r\n", b"\n"}:
			break
		name, separator, value = line.partition(b":")
		if separator and name.strip().lower() == b"content-length":
			content_length = int(value.strip())
	if content_length is None or content_length < 0:
		return None
	body = sys.stdin.buffer.read(content_length)
	if len(body) != content_length:
		return None
	value = json.loads(body.decode("utf-8"))
	return value if isinstance(value, dict) else None


def send_message(value: dict[str, Any]) -> None:
	body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
	sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
	sys.stdout.buffer.write(body)
	sys.stdout.buffer.flush()


def result_for(message: dict[str, Any]) -> Any:
	method = message.get("method")
	if method == "initialize":
		return {
			"capabilities": {
				"hoverProvider": True,
				"signatureHelpProvider": {"triggerCharacters": ["("]},
				"textDocumentSync": 1,
			},
			"serverInfo": {"name": "access-link-test-lsp", "version": "1"},
		}
	if method == "textDocument/signatureHelp":
		position = message.get("params", {}).get("position", {})
		# A cursor on the name or opening parenthesis is normalized just inside
		# the call. A cursor on the closing parenthesis is already inside in LSP
		# coordinates. Neither case moves the real editor cursor.
		if position.get("character") not in {16, 31}:
			return None
		return {
			"activeSignature": 0,
			"activeParameter": 1,
			"signatures": [
				{
					"label": "calculate_total(price: float, quantity: int) -> float",
					"documentation": {
						"kind": "markdown",
						"value": "Calculate a total through a real LSP round trip.",
					},
					"parameters": [
						{"label": "price: float"},
						{
							"label": "quantity: int",
							"documentation": "Number of items.",
						},
					],
				}
			],
		}
	if method == "textDocument/hover":
		return {
			"contents": {
				"kind": "markdown",
				"value": "Real hover fallback from the test LSP server.",
			},
		}
	if method == "shutdown":
		return None
	return None


def main() -> int:
	while True:
		message = read_message()
		if message is None:
			return 0
		if message.get("method") == "exit":
			return 0
		if "id" in message:
			send_message(
				{
					"jsonrpc": "2.0",
					"id": message["id"],
					"result": result_for(message),
				}
			)


if __name__ == "__main__":
	raise SystemExit(main())
