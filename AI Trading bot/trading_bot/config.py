from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
WEB_DIR = ROOT_DIR / "web"
CLOUD_DIR = ROOT_DIR / "cloud"
MCP_DIR = ROOT_DIR / "mcp"

SETTINGS_PATH = DATA_DIR / "settings.json"
TRADES_JSON_PATH = DATA_DIR / "trades.json"
STRATEGY_PATH = DATA_DIR / "strategy.md"
LEDGER_PATH = DATA_DIR / "trade-ledger.md"
LEARNING_PATH = DATA_DIR / "learning-file.md"

DEFAULT_SETTINGS: dict[str, Any] = {
    "mode": "demo",
    "dry_run": True,
    "default_instrument": "BTC-USDT",
    "poll_seconds": 30,
    "blofin": {
        "api_key": "[insert key]",
        "api_secret": "[insert secret]",
        "passphrase": "[insert passphrase]",
        "base_url": "https://demo-trading-openapi.blofin.com",
    },
    "strategy_profile": {
        "name": "Core Trend Continuation",
        "risk_per_trade_pct": 1.0,
        "max_open_positions": 2,
        "timeframes": ["15m", "1H", "4H"],
        "entry_checklist": [
            "Trend bias aligns with higher timeframe structure.",
            "Liquidity sweep or reclaim confirms the trigger.",
            "Invalidation level is defined before entry.",
        ],
        "exit_checklist": [
            "First target reached.",
            "Stop loss invalidated the thesis.",
            "Structure changed against the position.",
        ],
    },
    "cloud_memory": {
        "enabled": False,
        "provider": "local_markdown",
        "supabase_url": "",
        "supabase_service_role": "",
        "supabase_trades_table": "trades",
        "supabase_reflections_table": "reflections",
        "supermemory_api_key": "",
    },
}

DEFAULT_STRATEGY = """# Trading Strategy

Updated: 2026-08-18

## Source Context
- Requested build date: 2026-08-18
- Brain dump status: not supplied yet
- Action needed: replace the bracketed prompts below with your real playbook

## Strategy Identity
- Strategy name: [Name your strategy]
- Primary market: BloFin perpetual futures
- Core instruments: BTC-USDT, ETH-USDT, [add others]
- Trading style: intraday / swing / scalping [choose one]
- Market conditions favored: [trend / range / breakout / mean reversion]

## Bias Framework
- Higher timeframe map: [How you define directional bias]
- Session preference: [Asia / London / New York / overlap]
- News filter: [Which events make you stand down]
- Volatility filter: [How you decide conditions are tradable]

## Entry Model
1. Context trigger: [What must happen before you care]
2. Setup confirmation: [Structure, reclaim, sweep, divergence, etc.]
3. Entry execution: [Market / limit / ladder]
4. Invalidation: [Exact reason the trade is wrong]

## Risk Model
- Risk per trade: 1% default in the dashboard settings
- Max simultaneous positions: 2
- Daily loss cap: [Insert hard stop]
- Weekly drawdown rule: [Insert rule]
- Leverage rule: [Insert leverage limits by setup quality]

## Position Management
- Partial take profit rule: [Insert rule]
- Move-to-breakeven rule: [Insert rule]
- Full exit rule: [Insert rule]
- Time stop rule: [Insert rule]

## Journaling Requirements
- Every trade must log entry, exit, timing, setup, and notes
- Every trading day should include emotional context and execution grade
- Every week should end with one lesson and one process change

## Automation Rules
- Demo mode first until the win rate and process stability are proven
- Dry-run stays on until you are comfortable with the order payloads
- Any live deployment must use API keys with the least permissions required
- Bind API keys to trusted IP addresses where possible

## Review Cadence
- Daily: mark A-grade vs B-grade trades
- Weekly: review win rate, expectancy, and repeated mistakes
- Monthly: trim low-performing setups and reinforce what compounds
"""

DEFAULT_LEDGER = """# Trade Ledger

Updated automatically by the dashboard.

| Trade ID | Symbol | Side | Setup | Entry | Exit | Opened | Closed | PnL USD | PnL R | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""

DEFAULT_LEARNING = """# Learning File

This file is refreshed from the trade ledger.

Add trades in the dashboard, then use the refresh action to regenerate coaching notes and improvement ideas.
"""


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_project_files() -> None:
    for directory in (DATA_DIR, WEB_DIR, CLOUD_DIR, MCP_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    if not TRADES_JSON_PATH.exists():
        TRADES_JSON_PATH.write_text("[]\n", encoding="utf-8")

    if not STRATEGY_PATH.exists():
        STRATEGY_PATH.write_text(DEFAULT_STRATEGY, encoding="utf-8")

    if not LEDGER_PATH.exists():
        LEDGER_PATH.write_text(DEFAULT_LEDGER, encoding="utf-8")

    if not LEARNING_PATH.exists():
        LEARNING_PATH.write_text(DEFAULT_LEARNING, encoding="utf-8")


def load_settings() -> dict[str, Any]:
    ensure_project_files()
    raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return deep_merge(DEFAULT_SETTINGS, raw)


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    ensure_project_files()
    merged = deep_merge(load_settings(), settings)
    SETTINGS_PATH.write_text(json.dumps(merged, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return merged


def read_text(path: Path) -> str:
    ensure_project_files()
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_project_files()
    path.write_text(content, encoding="utf-8")
