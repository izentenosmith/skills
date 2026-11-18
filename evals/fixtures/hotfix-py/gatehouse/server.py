"""A minimal HTTP front for the endpoints. Tokens are looked up by the bearer value."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from gatehouse.api.exports import run_export
from gatehouse.api.reports import get_report
from gatehouse.tokens import issue

TOKENS = {
    "demo-reader": issue("demo-reader", ["reports:read"]),
}


class Handler(BaseHTTPRequestHandler):
    def _token(self):
        return TOKENS.get(self.headers.get("Authorization", "").removeprefix("Bearer "))

    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        token = self._token()
        if token is None or not self.path.startswith("/reports/"):
            return self._send(404, {"error": "not_found"})
        self._send(*get_report(token, self.path.removeprefix("/reports/")))

    def do_POST(self):
        token = self._token()
        if token is None or self.path != "/exports":
            return self._send(404, {"error": "not_found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        self._send(*run_export(token, body.get("report", "")))


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
