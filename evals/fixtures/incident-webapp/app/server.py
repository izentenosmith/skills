import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.pricing import price


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        total = sum(price(body["user_id"], l["unit_cents"], l["qty"]) for l in body["lines"])
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"total_cents": total}).encode())


if __name__ == "__main__":
    HTTPServer(("", 8080), Handler).serve_forever()
