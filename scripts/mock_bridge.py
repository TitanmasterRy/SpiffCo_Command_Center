"""Mock SpiffCoBridge: a stand-in for the in-game command bridge mod.

Implements the same HTTP contract as the SpiffCoBridge UE plugin
(``bridge-mod/SpiffCoBridge``) so the SpiffCo admin panel's real-dispatch path
can be exercised without a running game:

    GET  /health   -> {"status": "ok", "world": "mock", "actions": ["*"]}
    POST /execute  -> {"action", "succeeded", "message"}; 401 on a bad token.

Usage::

    python scripts/mock_bridge.py [--port 8091] [--token SECRET]

Then point the backend at it::

    SPIFFCO_ADMIN_COMMAND_URL=http://localhost:8091
    SPIFFCO_ADMIN_COMMAND_TOKEN=SECRET

Every command received is printed to stdout. The mock accepts *all* action ids
(the real mod 501s the ones it hasn't implemented yet). Stdlib only.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = ""
TOGGLES: dict[str, bool] = {}


class Handler(BaseHTTPRequestHandler):
    """Implements the bridge contract; state is process-global (single world)."""

    def _send(self, code: int, body: dict[str, object]) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _authed(self) -> bool:
        return not TOKEN or self.headers.get("X-SpiffCo-Token", "") == TOKEN

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if not self._authed():
            self._send(401, {"error": "missing or invalid X-SpiffCo-Token"})
            return
        if self.path != "/health":
            self._send(404, {"error": f"no route {self.path}"})
            return
        self._send(200, {"status": "ok", "world": "mock", "actions": ["*"]})

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        if not self._authed():
            self._send(401, {"error": "missing or invalid X-SpiffCo-Token"})
            return
        if self.path != "/execute":
            self._send(404, {"error": f"no route {self.path}"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            action = body["action"]
        except (ValueError, KeyError):
            self._send(422, {"error": "body must be JSON with an 'action'"})
            return

        enabled = body.get("enabled")
        if isinstance(enabled, bool):
            TOGGLES[action] = enabled
        state = "" if enabled is None else f" enabled={enabled}"
        print(f"[mock-bridge] {action} params={body.get('params', {})}{state}", flush=True)
        self._send(200, {"action": action, "succeeded": True,
                         "message": f"mock-executed {action}"})

    def log_message(self, *_: object) -> None:
        """Silence the default per-request access log (we print commands)."""


def main() -> None:
    """Parse args and serve until interrupted."""
    global TOKEN
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--token", default="", help="require this X-SpiffCo-Token")
    args = parser.parse_args()
    TOKEN = args.token

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    auth = "token required" if TOKEN else "NO auth"
    print(f"[mock-bridge] listening on :{args.port} ({auth}); Ctrl-C to stop", flush=True)
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()


if __name__ == "__main__":
    main()
