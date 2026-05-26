"""Run the Switch It Up frontend and JSON API from one local server."""

from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from src.backend import BackendError, JsonStore, SwitchItUpBackend


ROOT = Path(__file__).resolve().parent
DATA_PATH = Path(os.environ.get("SWITCHITUP_DATA_PATH", ROOT / "data" / "app_state.json"))
MAX_BODY_BYTES = 10 * 1024 * 1024
backend = SwitchItUpBackend(JsonStore(DATA_PATH))


class SwitchItUpHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", os.environ.get("SWITCHITUP_CORS_ORIGIN", "*"))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True, "service": "switchitup-api", "version": "0.3.0"})
            return
        if path == "/api/state":
            self._send_json(backend.get_state())
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/profile/role":
                self._send_json(backend.set_role(str(payload.get("role", ""))))
            elif path == "/api/profile/measurements":
                self._send_json(backend.update_measurements(payload))
            elif path == "/api/stylist/upgrade":
                self._send_json(backend.upgrade_stylist_account(payload), status=201)
            elif path == "/api/wardrobe":
                self._send_json(backend.add_wardrobe_item(payload), status=201)
            elif path == "/api/outfit/select":
                self._send_json(backend.select_item(str(payload.get("name", ""))))
            elif path == "/api/scan":
                self._send_json(backend.complete_scan(int(payload.get("quality", 96))))
            elif path == "/api/style-requests":
                self._send_json(backend.create_style_request(payload), status=201)
            elif path == "/api/wishlist":
                self._send_json(
                    backend.wishlist_action(str(payload.get("item", "")), str(payload.get("action", "")))
                )
            elif path == "/api/social/posts":
                self._send_json(backend.create_post(payload), status=201)
            elif path == "/api/social/react":
                self._send_json(backend.react_to_post(payload))
            elif path == "/api/messages":
                self._send_json(backend.send_message(payload), status=201)
            elif path == "/api/mall/register":
                self._send_json(backend.register_mall(payload), status=201)
            elif path == "/api/competitions":
                self._send_json(backend.create_competition(payload), status=201)
            elif path == "/api/competitions/entries":
                self._send_json(backend.submit_competition_entry(payload), status=201)
            elif path == "/api/stylists/follow":
                self._send_json(backend.follow_stylist(payload))
            elif path == "/api/reset":
                self._send_json(backend.reset())
            else:
                self._send_json({"error": "not found"}, status=404)
        except BackendError as error:
            self._send_json({"error": str(error)}, status=error.status)
        except json.JSONDecodeError:
            self._send_json({"error": "request body must be valid JSON"}, status=400)
        except Exception as error:
            self.log_error("Unhandled API error: %r", error)
            self._send_json({"error": "internal server error"}, status=500)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise BackendError("Content-Length must be a number") from exc
        if length > MAX_BODY_BYTES:
            raise BackendError("request body is too large", status=413)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 5180) -> None:
    server = ThreadingHTTPServer((host, port), SwitchItUpHandler)
    print(f"Switch It Up backend running at http://{host}:{port}")
    print(f"API health check: http://{host}:{port}/api/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Switch It Up backend")
    finally:
        server.server_close()


if __name__ == "__main__":
    run(
        host=os.environ.get("SWITCHITUP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", os.environ.get("SWITCHITUP_PORT", "5180"))),
    )
