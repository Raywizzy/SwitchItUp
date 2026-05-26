"""Run the Switch It Up frontend and JSON API from one local server."""

from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from src.backend import BackendError, JsonStore, SwitchItUpBackend


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "app_state.json"
backend = SwitchItUpBackend(JsonStore(DATA_PATH))


class SwitchItUpHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True, "service": "switchitup-api"})
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
            elif path == "/api/reset":
                self._send_json(backend.reset())
            else:
                self._send_json({"error": "not found"}, status=404)
        except BackendError as error:
            self._send_json({"error": str(error)}, status=error.status)
        except json.JSONDecodeError:
            self._send_json({"error": "request body must be valid JSON"}, status=400)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
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
    run()
