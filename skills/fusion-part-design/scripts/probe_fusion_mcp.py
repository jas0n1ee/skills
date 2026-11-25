#!/usr/bin/env python3
"""Probe local Fusion MCP and optionally call its read tool; Python 3.9+."""

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18")


class ProbeError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProbeError("MCP redirected; verify the local endpoint before retrying")


def local_endpoint(value):
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "http"
            or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username or parsed.password or parsed.fragment or parsed.query):
        raise ProbeError("Use a local http://localhost, 127.0.0.1, or [::1] endpoint")
    return value


def read_response(response, request_id):
    """Stop at the matching SSE event; do not wait for a live stream to close."""
    if "text/event-stream" not in response.headers.get("Content-Type", ""):
        message = json.load(response)
        if not isinstance(message, dict) or message.get("id") != request_id:
            raise ProbeError("JSON response did not match the request ID")
        return message
    data = []
    for raw in response:
        line = raw.decode("utf-8").rstrip("\r\n")
        if line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
        elif not line and data:
            message = json.loads("\n".join(data))
            data = []
            if isinstance(message, dict) and message.get("id") == request_id:
                return message
    raise ProbeError("SSE ended without a matching response")


class Client:
    def __init__(self, endpoint, timeout):
        self.endpoint = local_endpoint(endpoint)
        self.timeout = timeout
        self.session = None
        self.protocol = None
        self.next_id = 1
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())

    def rpc(self, method, params=None, notification=False):
        request_id = self.next_id
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = request_id
        if params is not None:
            payload["params"] = params
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["MCP-Session-Id"] = self.session
        if self.protocol:
            headers["MCP-Protocol-Version"] = self.protocol
        request = urllib.request.Request(
            self.endpoint, json.dumps(payload).encode("utf-8"), headers, method="POST")
        with self.opener.open(request, timeout=self.timeout) as response:
            if method == "initialize":
                self.session = response.headers.get("MCP-Session-Id")
            if notification:
                return None
            message = read_response(response, request_id)
        if "error" in message:
            raise ProbeError(f"{method}: JSON-RPC error {message['error']}")
        result = message.get("result")
        if not isinstance(result, dict):
            raise ProbeError(f"{method}: missing result object")
        if result.get("isError"):
            raise ProbeError(f"{method}: tool reported isError: {result.get('content')}")
        return result

    def initialize(self, protocol):
        result = self.rpc("initialize", {
            "protocolVersion": protocol, "capabilities": {},
            "clientInfo": {"name": "fusion-part-design-probe", "version": "1.0"}})
        self.protocol = result.get("protocolVersion")
        if self.protocol not in PROTOCOLS:
            raise ProbeError(f"Unsupported negotiated protocol: {self.protocol}")
        self.rpc("notifications/initialized", notification=True)
        return result

    def list_tools(self):
        tools = []
        seen_cursors = set()
        params = {}
        for _ in range(100):
            result = self.rpc("tools/list", params)
            page = result.get("tools")
            if not isinstance(page, list):
                raise ProbeError("tools/list: tools must be an array")
            tools.extend(page)
            cursor = result.get("nextCursor")
            if not cursor:
                return {"tools": tools}
            if not isinstance(cursor, str) or cursor in seen_cursors:
                raise ProbeError("tools/list: invalid or repeated pagination cursor")
            seen_cursors.add(cursor)
            params = {"cursor": cursor}
        raise ProbeError("tools/list exceeded 100 pages")


def write_json(directory, filename, value):
    path = directory / filename
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.environ.get(
        "FUSION_MCP_ENDPOINT", "http://127.0.0.1:27182/mcp"))
    parser.add_argument("--protocol-version", choices=PROTOCOLS, default=PROTOCOLS[0])
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="Fresh local temporary directory outside the skill/project")
    parser.add_argument("--read-arguments", type=Path,
                        help="JSON arguments for fusion_mcp_read; inspect live schema first")
    args = parser.parse_args(argv)
    try:
        if args.timeout <= 0:
            raise ProbeError("Timeout must be positive")
        client = Client(args.endpoint, args.timeout)
        read_args = None
        if args.read_arguments:
            read_args = json.loads(args.read_arguments.read_text(encoding="utf-8-sig"))
            if not isinstance(read_args, dict):
                raise ProbeError("Read arguments must be a JSON object")
        output = args.output_dir.expanduser().resolve()
        skill_dir = Path(__file__).resolve().parents[1]
        if output == skill_dir or skill_dir in output.parents:
            raise ProbeError("Choose a temporary output directory outside the skill")
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise ProbeError("Output directory must be empty to avoid stale success records")
        initialized = client.initialize(args.protocol_version)
        write_json(output, "initialize.json", initialized)
        tools = client.list_tools()
        write_json(output, "tools.json", tools)
        names = [tool["name"] for tool in tools["tools"]]
        if read_args is not None:
            if "fusion_mcp_read" not in names:
                raise ProbeError("fusion_mcp_read is unavailable; inspect tools.json")
            result = client.rpc("tools/call", {
                "name": "fusion_mcp_read", "arguments": read_args})
            write_json(output, "read-result.json", result)
        print(json.dumps({"ok": True, "endpoint": client.endpoint,
                          "server": initialized.get("serverInfo"), "tools": names,
                          "read_performed": read_args is not None,
                          "output_dir": str(output)}, ensure_ascii=False))
        return 0
    except (ProbeError, OSError, ValueError, KeyError, TypeError) as error:
        # Do not log request headers/session identifiers, and never retry calls.
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
