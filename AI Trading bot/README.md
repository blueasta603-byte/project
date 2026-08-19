# AI Trading Bot

This folder contains a local BloFin trading dashboard scaffold with:

- BloFin API-ready settings
- A markdown strategy file
- A markdown trade ledger
- A markdown learning file
- Optional cloud-memory scaffolding for Supabase

## Run the dashboard

```bash
python app.py
```

Open `http://127.0.0.1:8000`.

## Defaults

- Mode starts in `demo`
- `dry_run` starts as `true`
- Your BloFin credentials live in `data/settings.json`
- `data/settings.json` is ignored by git in this folder

## Files

- `data/strategy.md`: your trading playbook
- `data/trade-ledger.md`: human-readable trade journal
- `data/learning-file.md`: auto-refreshed reflection notes
- `mcp/blofin-mcp.example.json`: example MCP server config
- `cloud/supabase-schema.sql`: optional cloud schema

## Notes

- The strategy file includes placeholders because your actual brain dump was not provided in this request.
- The learning file is generated locally from heuristics and is also ready for deeper LLM review prompts.
- Live trading requires you to disable dry-run mode yourself after testing.

