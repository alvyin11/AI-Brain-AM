# AM Digital KE — AI SEO Brain (LangGraph edition)

Python LangGraph service replacing the n8n AI Brain agent. Same chat UI contract,
same Supabase data layer (`rpc_*` functions), same Qdrant knowledge base.

- **Setup + deploy + cutover:** see `HANDOVER — LangGraph Brain.md` in the parent folder
  (`F:\Claude Code\NEW AM Digital KE Articles\Supabase-langgraph migration\n8n-superbase and langgraph\`).
- **Credentials:** copy `.env.example` → `.env` and fill (never committed).
- **System prompt:** `app/prompts/system.txt` — generated from the n8n v2.2 brain by
  `gen_system_prompt.py` so both brains stay identical during the parallel run.
- **Run locally:** `pip install -r requirements.txt && uvicorn app.main:app --port 8001`
- **Docker:** `docker build -t amdk-brain . && docker run -d --env-file .env -p 8001:8001 amdk-brain`

Architecture: FastAPI → LangGraph ReAct agent (Sonnet 4.6 via OpenRouter) → 23 tools
(Supabase / WP REST / DataforSEO / Qdrant / GSC / GA4) → Postgres checkpointer (Supabase).
Four autonomous crons (Watchdog, Replenish, Outcome Review, Task Nudge) run in-process via APScheduler.
