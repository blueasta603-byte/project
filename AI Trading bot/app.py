from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from trading_bot.blofin_client import BlofinAPIError, BlofinClient
from trading_bot.cloud_memory import CloudMemoryRouter
from trading_bot.config import (
    LEARNING_PATH,
    STRATEGY_PATH,
    WEB_DIR,
    ensure_project_files,
    load_settings,
    read_text,
    save_settings,
    write_text,
)
from trading_bot.ledger import TradeLedger
from trading_bot.learning import LearningEngine


class AppState:
    def __init__(self) -> None:
        ensure_project_files()
        self.ledger = TradeLedger()
        self.learning = LearningEngine(self.ledger)
        self.memory = CloudMemoryRouter()


class TradingDashboardHandler(BaseHTTPRequestHandler):
    server_version = "AITradingDashboard/0.1"

    @property
    def state(self) -> AppState:
        return self.server.state  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self._serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path.startswith("/web/"):
            file_path = WEB_DIR / path.removeprefix("/web/")
            self._serve_file(file_path)
            return

        if path == "/api/status":
            settings = load_settings()
            self._send_json(
                200,
                {
                    "ok": True,
                    "mode": settings["mode"],
                    "dry_run": settings["dry_run"],
                    "default_instrument": settings["default_instrument"],
                    "blofin_configured": BlofinClient(settings).is_configured,
                    "cloud_memory": self.state.memory.health(settings),
                },
            )
            return

        if path == "/api/config":
            self._send_json(200, {"settings": load_settings()})
            return

        if path == "/api/strategy":
            self._send_json(200, {"content": read_text(STRATEGY_PATH)})
            return

        if path == "/api/ledger":
            entries = self.state.ledger.load_entries()
            self._send_json(
                200,
                {
                    "entries": entries,
                    "stats": self.state.ledger.build_stats(entries),
                    "markdown": self.state.ledger.read_markdown(),
                },
            )
            return

        if path == "/api/learning":
            self._send_json(200, {"content": read_text(LEARNING_PATH)})
            return

        if path == "/api/market":
            settings = load_settings()
            inst_id = query.get("instId", [settings["default_instrument"]])[0]
            bar = query.get("bar", ["1H"])[0]
            client = BlofinClient(settings)
            try:
                payload = client.get_market_snapshot(inst_id=inst_id, bar=bar)
                self._send_json(200, payload)
            except BlofinAPIError as exc:
                self._send_json(502, {"error": str(exc)})
            return

        if path == "/api/account":
            settings = load_settings()
            inst_id = query.get("instId", [settings["default_instrument"]])[0]
            client = BlofinClient(settings)
            if not client.is_configured:
                self._send_json(
                    200,
                    {
                        "configured": False,
                        "message": "Add your BloFin API key, secret, and passphrase in Settings to unlock private account data.",
                    },
                )
                return
            try:
                payload = client.get_account_snapshot(inst_id=inst_id)
                self._send_json(200, payload)
            except BlofinAPIError as exc:
                self._send_json(502, {"error": str(exc)})
            return

        self._send_json(404, {"error": f"Unknown route: {path}"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        if path == "/api/config":
            settings = save_settings(body.get("settings", {}))
            self._send_json(
                200,
                {
                    "ok": True,
                    "message": "Settings saved.",
                    "settings": settings,
                    "cloud_memory": self.state.memory.health(settings),
                },
            )
            return

        if path == "/api/strategy":
            content = body.get("content", "")
            if not content.endswith("\n"):
                content += "\n"
            write_text(STRATEGY_PATH, content)
            self._send_json(200, {"ok": True, "message": "Strategy file updated."})
            return

        if path == "/api/ledger":
            settings = load_settings()
            entry = self.state.ledger.add_entry(body)
            cloud_result = self.state.memory.sync_trade(settings, entry)
            learning_md = self.state.learning.refresh(settings)
            reflection_result = self.state.memory.sync_reflection(settings, learning_md)
            self._send_json(
                201,
                {
                    "ok": True,
                    "message": "Trade added to the ledger.",
                    "entry": entry,
                    "stats": self.state.ledger.build_stats(self.state.ledger.load_entries()),
                    "cloud_memory": cloud_result,
                    "reflection_sync": reflection_result,
                },
            )
            return

        if path == "/api/learning/refresh":
            settings = load_settings()
            content = self.state.learning.refresh(settings)
            reflection_result = self.state.memory.sync_reflection(settings, content)
            self._send_json(
                200,
                {
                    "ok": True,
                    "message": "Learning file refreshed.",
                    "content": content,
                    "reflection_sync": reflection_result,
                },
            )
            return

        if path == "/api/order":
            settings = load_settings()
            client = BlofinClient(settings)
            if not client.is_configured:
                self._send_json(400, {"error": "BloFin credentials are not configured."})
                return

            if settings["dry_run"]:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "dry_run": True,
                        "message": "Dry-run mode is enabled. No order was sent to BloFin.",
                        "preview": body,
                    },
                )
                return

            try:
                result = client.place_order(body)
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "dry_run": False,
                        "message": "Order submitted to BloFin.",
                        "result": result,
                    },
                )
            except BlofinAPIError as exc:
                self._send_json(502, {"error": str(exc)})
            return

        self._send_json(404, {"error": f"Unknown route: {path}"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self._send_json(404, {"error": f"File not found: {path.name}"})
            return
        mime = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    ensure_project_files()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), TradingDashboardHandler)
    server.state = AppState()  # type: ignore[attr-defined]
    print("Dashboard running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
