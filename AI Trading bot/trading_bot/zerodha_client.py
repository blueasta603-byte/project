from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ZerodhaAPIError(RuntimeError):
    """Raised when the Zerodha Kite API returns an error or invalid payload."""


@dataclass
class ZerodhaKiteClient:
    settings: dict[str, Any]

    @property
    def config(self) -> dict[str, Any]:
        return self.settings["zerodha"]

    @property
    def base_url(self) -> str:
        return "https://api.kite.trade"

    @property
    def login_base_url(self) -> str:
        return "https://kite.zerodha.com/connect/login"

    @property
    def is_api_configured(self) -> bool:
        return all(not self._looks_like_placeholder(self.config.get(key, "")) for key in ("api_key", "api_secret"))

    @property
    def has_access_token(self) -> bool:
        return not self._looks_like_placeholder(self.config.get("access_token", ""))

    def login_url(self) -> str:
        if not self.is_api_configured:
            raise ZerodhaAPIError("Add your Zerodha API key and API secret before opening the Kite login flow.")
        return f"{self.login_base_url}?{urlencode({'v': '3', 'api_key': self.config['api_key']})}"

    def generate_session(self, request_token: str) -> dict[str, Any]:
        if not self.is_api_configured:
            raise ZerodhaAPIError("Zerodha API key and secret are required to exchange a request token.")
        checksum = hashlib.sha256(
            f"{self.config['api_key']}{request_token}{self.config['api_secret']}".encode("utf-8")
        ).hexdigest()
        return self._request(
            "POST",
            "/session/token",
            body={
                "api_key": self.config["api_key"],
                "request_token": request_token,
                "checksum": checksum,
            },
            auth=False,
            form_encoded=True,
        )

    def invalidate_session(self) -> Any:
        if not (self.is_api_configured and self.has_access_token):
            return {"cleared": True}
        return self._request(
            "DELETE",
            "/session/token",
            body={
                "api_key": self.config["api_key"],
                "access_token": self.config["access_token"],
            },
            auth=True,
            form_encoded=True,
        )

    def get_market_snapshot(self, instrument: str, interval: str = "15minute") -> dict[str, Any]:
        instrument_key = self._normalize_instrument(instrument)
        quote_map = self.auth_get("/quote", {"i": [instrument_key]})
        quote = quote_map.get(instrument_key, {})
        ohlc_map = self.auth_get("/quote/ohlc", {"i": [instrument_key]})
        ltp_map = self.auth_get("/quote/ltp", {"i": [instrument_key]})

        historical: list[dict[str, Any]] = []
        instrument_token = quote.get("instrument_token")
        if instrument_token:
            historical = self.get_historical_candles(int(instrument_token), interval)

        return {
            "instrument": instrument_key,
            "quote": quote,
            "ohlc": ohlc_map.get(instrument_key, {}),
            "ltp": ltp_map.get(instrument_key, {}),
            "candles": historical,
        }

    def get_historical_candles(self, instrument_token: int, interval: str) -> list[dict[str, Any]]:
        from_dt, to_dt = self._historical_window(interval)
        payload = self.auth_get(
            f"/instruments/historical/{instrument_token}/{interval}",
            {
                "from": from_dt,
                "to": to_dt,
                "oi": 1,
            },
        )
        candles = payload.get("candles", [])
        rows: list[dict[str, Any]] = []
        for candle in candles:
            row = {
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5],
            }
            if len(candle) > 6:
                row["oi"] = candle[6]
            rows.append(row)
        return rows

    def get_account_snapshot(self) -> dict[str, Any]:
        margins = self.auth_get("/user/margins")
        holdings = self.auth_get("/portfolio/holdings")
        positions = self.auth_get("/portfolio/positions")
        orders = self.auth_get("/orders")
        profile = self.auth_get("/user/profile")
        return {
            "configured": True,
            "profile": profile,
            "margins": margins,
            "holdings": holdings,
            "positions": positions,
            "orders": orders,
        }

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        exchange, tradingsymbol = self.parse_exchange_symbol(order.get("instrument", ""))
        payload = {
            "exchange": order.get("exchange") or exchange,
            "tradingsymbol": order.get("tradingsymbol") or tradingsymbol,
            "transaction_type": str(order.get("transaction_type", "BUY")).upper(),
            "quantity": str(order.get("quantity", "")),
            "product": str(order.get("product", "CNC")).upper(),
            "order_type": str(order.get("order_type", "MARKET")).upper(),
            "validity": str(order.get("validity", "DAY")).upper(),
            "variety": str(order.get("variety", "regular")).lower(),
        }
        optional_fields = (
            "price",
            "trigger_price",
            "disclosed_quantity",
            "tag",
            "validity_ttl",
            "squareoff",
            "stoploss",
            "trailing_stoploss",
        )
        for field in optional_fields:
            value = order.get(field)
            if value not in (None, ""):
                payload[field] = str(value)

        variety = payload.pop("variety")
        if not payload["exchange"] or not payload["tradingsymbol"]:
            raise ZerodhaAPIError("Use an instrument like NSE:INFY or fill both exchange and tradingsymbol.")
        if not payload["quantity"]:
            raise ZerodhaAPIError("Quantity is required for Zerodha order placement.")

        result = self._request(
            "POST",
            f"/orders/{variety}",
            body=payload,
            auth=True,
            form_encoded=True,
        )
        return {"order_id": result.get("order_id"), "raw": result}

    def auth_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params, auth=True)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = False,
        form_encoded: bool = False,
    ) -> Any:
        if auth and not self.has_access_token:
            raise ZerodhaAPIError("Kite access token is missing. Log in from the dashboard first.")

        query = self._encode_params(params)
        request_path = f"{path}?{query}" if query else path
        url = f"{self.base_url}{request_path}"
        data = None
        headers = {"X-Kite-Version": "3"}

        if auth:
            headers["Authorization"] = f"token {self.config['api_key']}:{self.config['access_token']}"

        if body is not None:
            if form_encoded:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                data = self._encode_params(body).encode("utf-8")
            else:
                headers["Content-Type"] = "application/json"
                data = json.dumps(body, separators=(",", ":")).encode("utf-8")

        request = Request(url=url, data=data, headers=headers, method=method.upper())

        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network behavior varies
            raise ZerodhaAPIError(f"Zerodha request failed: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ZerodhaAPIError("Zerodha returned non-JSON data.") from exc

        if payload.get("status") != "success":
            message = payload.get("message") or payload.get("error_type") or "Zerodha returned an unknown error."
            raise ZerodhaAPIError(message)
        return payload.get("data", {})

    def parse_exchange_symbol(self, instrument: str) -> tuple[str, str]:
        normalized = self._normalize_instrument(instrument)
        if ":" not in normalized:
            return "NSE", normalized
        exchange, tradingsymbol = normalized.split(":", 1)
        return exchange.upper(), tradingsymbol.upper()

    def _normalize_instrument(self, instrument: str) -> str:
        raw = str(instrument or "").strip().upper()
        if not raw:
            return "NSE:INFY"
        if ":" not in raw:
            return f"NSE:{raw}"
        return raw

    def _encode_params(self, params: dict[str, Any] | None) -> str:
        if not params:
            return ""
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            if value in (None, ""):
                continue
            normalized[key] = value
        return urlencode(normalized, doseq=True)

    def _looks_like_placeholder(self, value: str) -> bool:
        text = str(value).strip()
        return not text or text.startswith("[") or text.lower().startswith("insert ") or text.lower().startswith("your-")

    def _historical_window(self, interval: str) -> tuple[str, str]:
        now = datetime.utcnow()
        if interval == "day":
            start = now - timedelta(days=90)
        elif interval in {"60minute", "30minute"}:
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(days=7)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")
