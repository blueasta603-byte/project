# Cloud Memory

This project uses local markdown and JSON files by default. That is the safest setup for early testing.

If you outgrow local files, the scaffold already supports a Supabase-style sync path:

1. Create the tables from `supabase-schema.sql`.
2. Put your Supabase project URL and service role key into `data/settings.json`.
3. Set `cloud_memory.enabled` to `true`.
4. Set `cloud_memory.provider` to `supabase`.

`supermemory` is included as a configuration placeholder only. The local code does not call a Supermemory API yet.

