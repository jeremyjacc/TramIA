"""API HTTP sin dependencias externas para TramIA."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .service import TramService
from .web import LANDING_PAGE


ROOT = Path(__file__).resolve().parents[1]
service = TramService(os.getenv("TRAMIA_DB", str(ROOT / "tramia.db")))


class TramHandler(BaseHTTPRequestHandler):
    def _send(self, status: HTTPStatus, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, payload: str) -> None:
        data = payload.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("El cuerpo JSON es obligatorio.")
        parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("El cuerpo debe ser un objeto JSON.")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/":
            self._send_html(LANDING_PAGE)
            return
        if path == "/api/funcionarios/pendientes":
            self._send(HTTPStatus.OK, service.database.pending_human_reviews())
            return
        if path.startswith("/api/solicitudes/"):
            try:
                request_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self._send(HTTPStatus.BAD_REQUEST, {"error": "Identificador invalido."})
                return
            request = service.database.get_request(request_id)
            self._send(HTTPStatus.OK if request else HTTPStatus.NOT_FOUND, request or {"error": "Solicitud no encontrada."})
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        try:
            payload = self._read_json()
            if path == "/api/solicitudes":
                self._send(HTTPStatus.CREATED, service.submit(payload))
                return
            if path.startswith("/api/solicitudes/") and path.endswith("/escalar"):
                request_id = int(path.split("/")[3])
                result = service.escalate(request_id, str(payload.get("reason", "")))
                self._send(HTTPStatus.OK if result else HTTPStatus.NOT_FOUND, result or {"error": "Solicitud no encontrada."})
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        return


def run() -> None:
    host, port = "127.0.0.1", 8001
    server = ThreadingHTTPServer((host, port), TramHandler)
    print(f"TramIA disponible en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
