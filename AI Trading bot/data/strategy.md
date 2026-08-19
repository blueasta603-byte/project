# Trading Strategy

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

