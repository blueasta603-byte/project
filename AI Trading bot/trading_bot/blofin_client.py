from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


class BlofinAPIError(RuntimeError):
    """Raised when the BloFin API returns an error or invalid payload."""


@dataclass
class BlofinClient:
    settings: dict[str, Any]

    @property
    def config(self) -> dict[str, Any]:
        return self.settings["blofin"]

    @property
    def base_url(self) -> str:
        return self.config["base_url"].rstrip("/")

    @property
    def is_configured(self) -> bool:
        return all(not self._looks_like_placeholder(self.config.get(key, "")) for key in ("api_key", "api_secret", "passphrase"))

    def get_market_snapshot(self, inst_id: str, bar: str = "1H") -> dict[str, Any]:
        ticker = self.public_get("/api/v1/market/tickers", {"instId": inst_id})
        mark_price = self.public_get("/api/v1/market/mark-price", {"instId": inst_id})
        candles = self.public_get("/api/v1/market/candles", {"instId": inst_id, "bar": bar, "limit": "24"})
        instruments = self.public_get("/api/v1/market/instruments", {"instId": inst_id})
        return {
            "instrument": inst_id,
            "ticker": ticker[0] if ticker else {},
            "mark_price": mark_price[0] if mark_price else {},
            "instrument_meta": instruments[0] if instruments else {},
            "candles": [
                {
                    "ts": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                    "confirm": row[8],
                }
                for row in candles
            ],
        }

    def get_account_snapshot(self, inst_id: str) -> dict[str, Any]:
        return {
            "configured": True,
            "balances": self.private_get("/api/v1/asset/balances", {"accountType": "futures"}),
            "positions": self.private_get("/api/v1/account/positions", {"instId": inst_id}),
            "open_orders": self.private_get("/api/v1/trade/orders-pending", {"instId": inst_id}),
            "apikey": self.private_get("/api/v1/user/query-apikey"),
        }

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "instId": str(order["instId"]),
            "marginMode": str(order.get("marginMode", "cross")),
            "positionSide": str(order.get("positionSide", "net")),
            "side": str(order["side"]),
            "orderType": str(order.get("orderType", "market")),
            "size": str(order["size"]),
            "clientOrderId": str(order.get("clientOrderId", "")),
        }
        if order.get("price") not in (None, ""):
            payload["price"] = str(order["price"])
        if order.get("reduceOnly") not in (None, ""):
            payload["reduceOnly"] = str(order["reduceOnly"]).lower()
        return self.private_post("/api/v1/trade/order", payload)

    def public_get(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        return self._request("GET", path, params=params, auth=False)

    def private_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params, auth=True)

    def private_post(self, path: str, body: dict[str, Any]) -> Any:
        return self._request("POST", path, body=body, auth=True)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = False,
    ) -> Any:
        query = self._encode_params(params)
        request_path = f"{path}?{query}" if query else path
        url = f"{self.base_url}{request_path}"
        body_text = json.dumps(body, separators=(",", ":")) if body else ""
        data = body_text.encode("utf-8") if body_text else None

        headers = {"Content-Type": "application/json"}
        if auth:
            if not self.is_configured:
                raise BlofinAPIError("BloFin API credentials are missing or still using placeholders.")
            headers.update(self._auth_headers(method, request_path, body_text))

        request = Request(url=url, data=data, headers=headers, method=method.upper())

        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network behavior varies
            raise BlofinAPIError(f"BloFin request failed: {exc}") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BlofinAPIError("BloFin returned non-JSON data.") from exc

        if payload.get("code") != "0":
            raise BlofinAPIError(payload.get("msg", "BloFin returned an unknown error."))
        return payload.get("data", [])

    def _auth_headers(self, method: str, request_path: str, body_text: str) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid4())
        prehash = f"{request_path}{method.upper()}{timestamp}{nonce}{body_text}"
        hex_signature = hmac.new(
            self.config["api_secret"].encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().encode("utf-8")
        signature = base64.b64encode(hex_signature).decode("utf-8")
        return {
            "ACCESS-KEY": self.config["api_key"],
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-NONCE": nonce,
            "ACCESS-PASSPHRASE": self.config["passphrase"],
        }

    def _encode_params(self, params: dict[str, Any] | None) -> str:
        if not params:
            return ""
        normalized = {key: str(value) for key, value in params.items() if value not in (None, "")}
        return urlencode(normalized)

    def _looks_like_placeholder(self, value: str) -> bool:
        value = str(value).strip()
        return not value or value.startswith("[") or value.lower().startswith("insert ") or value.lower().startswith("your-")

