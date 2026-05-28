#!/usr/bin/env python3
"""
Minimal LSP server for OpenAPI specs.
Provides go-to-definition for operationId -> controller function.

Zero dependencies - raw JSON-RPC over stdio.
"""

import json
import os
import re
import subprocess
import sys


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def find_yaml_path(lines: list[str], segments: list[str]):
    """Walk a YAML file by indent and find the line of the exact key path.

    Returns (line_idx, indent_col) or None. Only handles plain mapping keys —
    no list items, anchors, or flow-style. Good enough for OpenAPI specs.
    """
    stack: list[tuple[int, str]] = []  # (indent, key) for current path

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)

        while stack and stack[-1][0] >= indent:
            stack.pop()

        m = re.match(r'["\']?([^"\':\s]+)["\']?\s*:', stripped)
        if not m:
            continue
        key = m.group(1)

        candidate = [k for _, k in stack] + [key]
        if candidate == segments:
            return (i, indent)

        stack.append((indent, key))

    return None


def read_message(stream) -> dict | None:
    """Read a JSON-RPC message from the LSP client. `stream` is a binary stream."""
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        key, _, value = line.partition(b": ")
        headers[key.decode("ascii")] = value.decode("ascii")

    length = int(headers.get("Content-Length", 0))
    if length == 0:
        return None

    # Content-Length is bytes per LSP spec; read from the binary stream.
    body = stream.read(length)
    return json.loads(body)


def send_message(stream, msg: dict):
    """Send a JSON-RPC message to the LSP client. `stream` is a binary stream."""
    body = json.dumps(msg).encode("utf-8")
    header = "Content-Length: {}\r\n\r\n".format(len(body)).encode("ascii")
    stream.write(header + body)
    stream.flush()


def respond(stream, id, result):
    send_message(stream, {"jsonrpc": "2.0", "id": id, "result": result})


def respond_error(stream, id, code, message):
    send_message(
        stream,
        {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}},
    )


class OpenApiLsp:
    def __init__(self):
        self.documents: dict[str, list[str]] = {}  # uri -> lines
        self.root_uri: str | None = None
        self.root_path: str | None = None

    def handle(self, msg: dict) -> dict | None:
        method = msg.get("method", "")
        params = msg.get("params", {})
        msg_id = msg.get("id")

        if method == "initialize":
            self.root_uri = params.get("rootUri")
            if self.root_uri and self.root_uri.startswith("file://"):
                self.root_path = self.root_uri[len("file://") :]
            return {
                "capabilities": {
                    "definitionProvider": True,
                    "textDocumentSync": {
                        "openClose": True,
                        "change": 1,  # Full sync
                    },
                }
            }

        elif method == "initialized":
            return None

        elif method == "shutdown":
            return None  # result: null

        elif method == "exit":
            sys.exit(0)

        elif method == "textDocument/didOpen":
            uri = params["textDocument"]["uri"]
            text = params["textDocument"]["text"]
            self.documents[uri] = text.splitlines()

        elif method == "textDocument/didChange":
            uri = params["textDocument"]["uri"]
            # Full sync: take the last content change
            changes = params.get("contentChanges", [])
            if changes:
                self.documents[uri] = changes[-1]["text"].splitlines()

        elif method == "textDocument/didClose":
            uri = params["textDocument"]["uri"]
            self.documents.pop(uri, None)

        elif method == "textDocument/definition":
            return self._handle_definition(params)

        return None

    def _handle_definition(self, params: dict):
        uri = params["textDocument"]["uri"]
        line_num = params["position"]["line"]
        lines = self.documents.get(uri, [])

        if line_num >= len(lines):
            return None

        line = lines[line_num]

        ref_match = re.match(
            r'''\s*\$ref:\s*["']?([^"'#\s]*)#(/[^"'\s]+)["']?\s*$''', line
        )
        if ref_match:
            rel_path, pointer = ref_match.group(1), ref_match.group(2)
            return self._resolve_ref(uri, rel_path, pointer)

        op_match = re.match(r"\s*operationId:\s*(.+?)\s*$", line)
        if op_match:
            operation_id = op_match.group(1)
            func_name = camel_to_snake(operation_id)
            return self._find_definition(func_name)

        return None

    def _resolve_ref(self, current_uri: str, rel_path: str, pointer: str):
        if not current_uri.startswith("file://"):
            return None
        current_path = current_uri[len("file://") :]

        if rel_path:
            target_path = os.path.normpath(
                os.path.join(os.path.dirname(current_path), rel_path)
            )
        else:
            target_path = current_path

        # JSON pointer escapes: ~1 -> /, ~0 -> ~
        segments = [
            seg.replace("~1", "/").replace("~0", "~")
            for seg in pointer.split("/")
            if seg
        ]
        if not segments:
            return None

        target_uri = "file://" + os.path.abspath(target_path)
        if target_uri in self.documents:
            target_lines = self.documents[target_uri]
        else:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    target_lines = f.read().splitlines()
            except (OSError, UnicodeDecodeError):
                return None

        found = find_yaml_path(target_lines, segments)
        if not found:
            return None
        line_idx, col = found
        return {
            "uri": target_uri,
            "range": {
                "start": {"line": line_idx, "character": col},
                "end": {
                    "line": line_idx,
                    "character": col + len(segments[-1]),
                },
            },
        }

    def _find_definition(self, func_name: str):
        search_dir = self.root_path or os.getcwd()
        pattern = f"def {func_name}("

        try:
            result = subprocess.run(
                [
                    "rg",
                    "--vimgrep",
                    "--fixed-strings",
                    pattern,
                    "--glob",
                    "!**/generated/**",
                    "--glob",
                    "!**/.claude/**",
                    search_dir,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        locations = []
        for line in result.stdout.strip().splitlines():
            m = re.match(r"^(.+?):(\d+):(\d+):(.*)$", line)
            if m:
                file_path, line_no, col_no, _ = m.groups()
                locations.append(
                    {
                        "uri": "file://" + os.path.abspath(file_path),
                        "range": {
                            "start": {
                                "line": int(line_no) - 1,
                                "character": int(col_no) - 1,
                            },
                            "end": {
                                "line": int(line_no) - 1,
                                "character": int(col_no) - 1 + len(func_name),
                            },
                        },
                    }
                )

        if len(locations) == 1:
            return locations[0]
        elif len(locations) > 1:
            return locations
        return None


def main():
    # Use binary streams so Content-Length (bytes per LSP spec) matches what
    # we read. Text-mode stdin would translate newlines and decode UTF-8 into
    # code points, which desyncs the byte count for non-ASCII payloads.
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    # Redirect text-mode stdin/stdout to /dev/null so stray prints can't
    # corrupt the LSP protocol.
    sys.stdin = open("/dev/null", "r")
    sys.stdout = open("/dev/null", "w")

    server = OpenApiLsp()

    while True:
        msg = read_message(stdin)
        if msg is None:
            break

        result = server.handle(msg)
        msg_id = msg.get("id")

        # Only respond to requests (messages with an id), not notifications
        if msg_id is not None:
            if result is None and msg.get("method") == "shutdown":
                respond(stdout, msg_id, None)
            elif result is not None:
                respond(stdout, msg_id, result)
            else:
                respond(stdout, msg_id, None)


if __name__ == "__main__":
    main()
