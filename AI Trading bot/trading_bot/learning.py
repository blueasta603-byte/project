from __future__ import annotations

from datetime import datetime
from typing import Any

from trading_bot.config import LEARNING_PATH, STRATEGY_PATH, read_text, write_text
from trading_bot.ledger import TradeLedger


def _now_label() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")


class LearningEngine:
    def __init__(self, ledger: TradeLedger) -> None:
        self.ledger = ledger

    def refresh(self, settings: dict[str, Any]) -> str:
        entries = self.ledger.load_entries()
        stats = self.ledger.build_stats(entries)
        strategy = read_text(STRATEGY_PATH)
        content = self._build_markdown(settings, stats, entries, strategy)
        write_text(LEARNING_PATH, content)
        return content

    def _build_markdown(
        self,
        settings: dict[str, Any],
        stats: dict[str, Any],
        entries: list[dict[str, Any]],
        strategy: str,
    ) -> str:
        suggestions = self._suggestions(stats, entries)
        recent = entries[:5]
        recent_lines = [
            f"- {item['opened_at']} | {item['symbol']} | {item['side']} | {item['setup']} | PnL USD: {item.get('pnl_usd', '') or 'n/a'}"
            for item in recent
        ] or ["- No trades logged yet."]

        return "\n".join(
            [
                "# Learning File",
                "",
                f"Updated: {_now_label()}",
                "",
                "## Performance Snapshot",
                f"- Mode: {settings['mode']}",
                f"- Dry run: {settings['dry_run']}",
                f"- Trades logged: {stats['trade_count']}",
                f"- Closed trades: {stats['closed_trade_count']}",
                f"- Win rate: {stats['win_rate']}%",
                f"- Total PnL USD: {stats['total_pnl_usd']}",
                f"- Average PnL USD: {stats['average_pnl_usd']}",
                f"- Average R: {stats['average_r']}",
                "",
                "## Recent Trades",
                *recent_lines,
                "",
                "## Reflection",
                *suggestions,
                "",
                "## Next Review Questions",
                "- Which setup has the best payoff relative to emotional effort?",
                "- Are losses clustered around one session, timeframe, or execution style?",
                "- Did any trade break the written strategy without a valid exception?",
                "",
                "## Claude-Ready Prompt",
                "Use this when you want a deeper LLM review with the current strategy and ledger:",
                "```text",
                "Review my BloFin trading strategy and ledger. Identify recurring mistakes, strongest setups, weak filters, and the single highest-impact rule change for next week.",
                "```",
                "",
                "## Strategy Snapshot",
                strategy.rstrip(),
            ]
        ) + "\n"

    def _suggestions(self, stats: dict[str, Any], entries: list[dict[str, Any]]) -> list[str]:
        suggestions: list[str] = []
        if stats["trade_count"] < 5:
            suggestions.append("- Sample size is still small. Focus on collecting clean, comparable trades before changing the strategy.")
        if stats["closed_trade_count"] >= 5 and stats["win_rate"] < 45:
            suggestions.append("- Win rate is below 45%. Tighten the entry checklist and remove trades taken without full bias alignment.")
        if stats["average_r"] < 0:
            suggestions.append("- Average R is negative. Your invalidation may be too loose, or your profit-taking may be cutting winners early.")
        if stats["buy_side_avg_pnl"] > stats["sell_side_avg_pnl"] + 5:
            suggestions.append("- Long setups are outperforming shorts. Consider reducing short exposure until the short thesis has a clearer edge.")
        if stats["sell_side_avg_pnl"] > stats["buy_side_avg_pnl"] + 5:
            suggestions.append("- Short setups are outperforming longs. Review whether bullish trades are being forced against structure.")
        notes_count = sum(1 for entry in entries if entry.get("notes"))
        if entries and notes_count / len(entries) < 0.8:
            suggestions.append("- Too many trades are missing notes. Add brief execution notes so the learning loop has better context.")
        if not suggestions:
            suggestions.append("- Execution looks stable so far. Keep logging trades and compare A-grade setups against everything else.")
        return suggestions

