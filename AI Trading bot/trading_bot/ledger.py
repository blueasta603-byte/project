from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

from trading_bot.config import LEDGER_PATH, TRADES_JSON_PATH, ensure_project_files


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class TradeLedger:
    def __init__(self, trades_path: Path = TRADES_JSON_PATH, markdown_path: Path = LEDGER_PATH) -> None:
        self.trades_path = trades_path
        self.markdown_path = markdown_path
        ensure_project_files()

    def load_entries(self) -> list[dict[str, Any]]:
        ensure_project_files()
        return json.loads(self.trades_path.read_text(encoding="utf-8"))

    def add_entry(self, payload: dict[str, Any]) -> dict[str, Any]:
        entries = self.load_entries()
        entry = {
            "id": payload.get("id") or f"trade-{uuid4().hex[:8]}",
            "symbol": payload.get("symbol", "INFY"),
            "exchange": payload.get("exchange", "NSE"),
            "side": payload.get("side", "buy"),
            "product": payload.get("product", "CNC"),
            "setup": payload.get("setup", "unspecified"),
            "timeframe": payload.get("timeframe", "15m"),
            "entry_price": payload.get("entry_price", ""),
            "exit_price": payload.get("exit_price", ""),
            "stop_loss": payload.get("stop_loss", ""),
            "take_profit": payload.get("take_profit", ""),
            "size": payload.get("size", ""),
            "opened_at": payload.get("opened_at", _utc_now()),
            "closed_at": payload.get("closed_at", ""),
            "session": payload.get("session", ""),
            "pnl_inr": payload.get("pnl_inr", payload.get("pnl_usd", "")),
            "pnl_r": payload.get("pnl_r", ""),
            "grade": payload.get("grade", ""),
            "tags": payload.get("tags", []),
            "notes": payload.get("notes", ""),
            "created_at": _utc_now(),
        }
        entries.insert(0, entry)
        self._save_entries(entries)
        self._sync_markdown(entries)
        return entry

    def build_stats(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        pnl_inr_values = [_to_float(item.get("pnl_inr", item.get("pnl_usd"))) for item in entries]
        pnl_r_values = [_to_float(item.get("pnl_r")) for item in entries]
        closed_entries = [item for item in entries if item.get("closed_at")]
        wins = [item for item in closed_entries if (_to_float(item.get("pnl_inr", item.get("pnl_usd"))) or 0.0) > 0]
        losses = [item for item in closed_entries if (_to_float(item.get("pnl_inr", item.get("pnl_usd"))) or 0.0) < 0]

        by_side: dict[str, list[float]] = {"buy": [], "sell": []}
        for item in entries:
            pnl = _to_float(item.get("pnl_inr", item.get("pnl_usd")))
            side = str(item.get("side", "")).lower()
            if pnl is not None and side in by_side:
                by_side[side].append(pnl)

        average_pnl = mean([value for value in pnl_inr_values if value is not None]) if any(value is not None for value in pnl_inr_values) else 0.0
        average_r = mean([value for value in pnl_r_values if value is not None]) if any(value is not None for value in pnl_r_values) else 0.0
        total_pnl = sum(value or 0.0 for value in pnl_inr_values)

        return {
            "trade_count": len(entries),
            "closed_trade_count": len(closed_entries),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": round((len(wins) / len(closed_entries) * 100.0), 2) if closed_entries else 0.0,
            "average_pnl_inr": round(average_pnl, 2),
            "average_r": round(average_r, 2),
            "total_pnl_inr": round(total_pnl, 2),
            "buy_side_avg_pnl": round(mean(by_side["buy"]), 2) if by_side["buy"] else 0.0,
            "sell_side_avg_pnl": round(mean(by_side["sell"]), 2) if by_side["sell"] else 0.0,
        }

    def read_markdown(self) -> str:
        ensure_project_files()
        return self.markdown_path.read_text(encoding="utf-8")

    def _save_entries(self, entries: list[dict[str, Any]]) -> None:
        self.trades_path.write_text(json.dumps(entries, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def _sync_markdown(self, entries: list[dict[str, Any]]) -> None:
        lines = [
            "# Trade Ledger",
            "",
            f"Last updated: {_utc_now()}",
            "",
            "| Trade ID | Symbol | Exchange | Side | Product | Setup | Entry | Exit | Opened | Closed | PnL INR | PnL R | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in entries:
            escaped = {key: self._escape_markdown_cell(value) for key, value in item.items()}
            lines.append(
                "| {id} | {symbol} | {exchange} | {side} | {product} | {setup} | {entry_price} | {exit_price} | {opened_at} | {closed_at} | {pnl_inr} | {pnl_r} | {notes} |".format(
                    **escaped
                )
            )
        self.markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _escape_markdown_cell(self, value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value).replace("|", "/").replace("\n", " ")
