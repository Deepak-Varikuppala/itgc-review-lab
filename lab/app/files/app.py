"""Northwind finance application: a small web page listing supplier payments.

Runs as the finance-app service on the app server and reads the finance database.
"""

from __future__ import annotations

import html
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB = os.environ.get("FINANCE_DB", "/var/lib/northwind/finance.db")
VERSION = (
    Path(__file__).with_name("VERSION").read_text().strip()
    if Path(__file__).with_name("VERSION").exists()
    else "unknown"
)


def payments() -> list[tuple]:
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as db:
        return db.execute(
            "SELECT p.id, s.name, p.amount, p.currency, p.created_by, p.approved_by, p.status "
            "FROM payments p JOIN suppliers s ON s.id = p.supplier_id ORDER BY p.id DESC LIMIT 50"
        ).fetchall()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body = b"ok\n"
            self.send_response(200)
        else:
            rows = "".join(
                "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>"
                for r in payments()
            )
            body = (
                f"<h1>Northwind payments</h1><p>Version {html.escape(VERSION)}</p>"
                "<table border=1><tr><th>ID</th><th>Supplier</th><th>Amount</th>"
                "<th>Currency</th><th>Created by</th><th>Approved by</th><th>Status</th></tr>"
                f"{rows}</table>"
            ).encode()
            self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
