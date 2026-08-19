from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen


class CloudMemoryRouter:
    def health(self, settings: dict[str, Any]) -> dict[str, Any]:
        cloud = settings["cloud_memory"]
        provider = cloud["provider"]
        enabled = bool(cloud["enabled"])
        if not enabled:
            return {"enabled": False, "provider": provider, "status": "local-only", "message": "Cloud memory is disabled."}
        if provider == "supabase" and cloud["supabase_url"] and cloud["supabase_service_role"]:
            return {"enabled": True, "provider": provider, "status": "ready", "message": "Supabase sync is configured."}
        if provider == "supermemory" and cloud["supermemory_api_key"]:
            return {
                "enabled": True,
                "provider": provider,
                "status": "partial",
                "message": "Supermemory is selected, but this scaffold only includes configuration placeholders.",
            }
        return {"enabled": True, "provider": provider, "status": "incomplete", "message": "Cloud memory is enabled but not fully configured."}

    def sync_trade(self, settings: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
        cloud = settings["cloud_memory"]
        if not cloud["enabled"]:
            return {"ok": True, "provider": "local_markdown", "message": "Stored locally only."}
        if cloud["provider"] == "supabase":
            return self._sync_supabase(settings, cloud["supabase_trades_table"], entry)
        if cloud["provider"] == "supermemory":
            return {"ok": False, "provider": "supermemory", "message": "Supermemory wiring is documented but not implemented in this local scaffold."}
        return {"ok": False, "provider": cloud["provider"], "message": "Unknown provider."}

    def sync_reflection(self, settings: dict[str, Any], content: str) -> dict[str, Any]:
        cloud = settings["cloud_memory"]
        if not cloud["enabled"]:
            return {"ok": True, "provider": "local_markdown", "message": "Reflection stored locally only."}
        if cloud["provider"] == "supabase":
            payload = {"created_at": datetime.utcnow().isoformat() + "Z", "content": content}
            return self._sync_supabase(settings, cloud["supabase_reflections_table"], payload)
        if cloud["provider"] == "supermemory":
            return {"ok": False, "provider": "supermemory", "message": "Supermemory wiring is documented but not implemented in this local scaffold."}
        return {"ok": False, "provider": cloud["provider"], "message": "Unknown provider."}

    def _sync_supabase(self, settings: dict[str, Any], table: str, payload: dict[str, Any]) -> dict[str, Any]:
        cloud = settings["cloud_memory"]
        url = cloud["supabase_url"].rstrip("/")
        token = cloud["supabase_service_role"]
        if not url or not token:
            return {"ok": False, "provider": "supabase", "message": "Supabase credentials are missing."}

        request = Request(
            url=f"{url}/rest/v1/{table}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "apikey": token,
                "Authorization": f"Bearer {token}",
                "Prefer": "return=minimal",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=10):
                return {"ok": True, "provider": "supabase", "table": table, "message": "Synced to Supabase."}
        except Exception as exc:  # pragma: no cover - network behavior varies
            return {"ok": False, "provider": "supabase", "table": table, "message": f"Supabase sync failed: {exc}"}

