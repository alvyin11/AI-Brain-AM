"""The brain graph: a ReAct agent with the super prompt, live client context,
Supabase-backed conversation checkpointing, and all 23 tools.

Checkpointing lives in Supabase Postgres (langgraph checkpointer tables are
created automatically on first run) — sessions survive restarts with no Redis
dependency. thread_id = the chat UI's sessionId."""
import time
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver

from app import config
from app.tools import ALL_TOOLS
from app.tools.db import get_brain_context

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.txt").read_text(encoding="utf-8")

_ctx_cache: dict = {"block": "", "ts": 0.0}


def build_context_block(force: bool = False) -> str:
    """Port of the n8n 'N8 — Build Context' node, with the same 15-minute cache."""
    now = time.time()
    if not force and _ctx_cache["block"] and now - _ctx_cache["ts"] < config.CONTEXT_CACHE_SECONDS:
        return _ctx_cache["block"]

    ctx = get_brain_context()
    cfg = ctx.get("client_config") or {}
    audits = ctx.get("audit_results") or []
    strat = ctx.get("audit_strategy") or {}
    lms = ctx.get("lead_magnets") or []
    clusters = ctx.get("cluster_taxonomy") or []
    wp_tax = ctx.get("wp_taxonomy") or []

    audit = next((a for a in audits if "[NOTE]" not in (a.get("audit_date") or "")), {})
    manual = " | ".join(a.get("technical_issues_summary") or "" for a in audits
                        if "[NOTE]" in (a.get("audit_date") or ""))

    L = ["=== LIVE CLIENT CONTEXT ==="]
    if cfg.get("client_name"):
        L.append(f"CLIENT: {cfg.get('client_name')} | {cfg.get('site_url')} | {cfg.get('industry', '')}")
        for label, key in [("VOICE", "brand_voice_notes"), ("GOAL 1", "primary_goal"),
                           ("GOAL 2", "secondary_goal"), ("AUDIENCE", "target_audience"),
                           ("STRATEGY", "current_strategy"), ("NOTES", "notes")]:
            if cfg.get(key):
                L.append(f"{label}: {cfg[key]}")
        comps = [cfg.get(f"competitor_{i}") for i in (1, 2, 3) if cfg.get(f"competitor_{i}")]
        if comps:
            L.append("COMPETITORS: " + " | ".join(comps))
    if audit.get("audit_date"):
        L.append(f"\nLATEST AUDIT: {audit['audit_date']} | Score: {audit.get('overall_health_score')}/50 "
                 f"| Indexed: {audit.get('total_indexed_pages')} pages")
        for label, key in [("TOP PAGES", "top_performing_pages"), ("BOTTOM PAGES", "bottom_performing_pages"),
                           ("TECH ISSUES", "technical_issues_summary"), ("KEYWORD GAPS", "keyword_gaps_summary"),
                           ("COMPETITOR DATA", "competitor_insights"),
                           ("RECOMMENDED FOCUS", "recommended_focus_next_30_days"),
                           ("MANUAL NOTES", "manual_notes")]:
            if audit.get(key):
                L.append(f"{label}: {audit[key]}")
        if manual:
            L.append("ADDITIONAL OBSERVATIONS: " + manual)
    if strat and strat.get("roadmap_30_days"):
        L.append("\n90-DAY ROADMAP:")
        for label, key in [("MONTH 1", "roadmap_30_days"), ("MONTH 2", "roadmap_60_days"),
                           ("MONTH 3", "roadmap_90_days"), ("KPI TARGETS", "kpi_targets"),
                           ("QUICK WINS", "quick_wins"), ("PRIORITY KEYWORDS", "priority_keywords")]:
            if strat.get(key):
                L.append(f"{label}: {strat[key]}")
    L.append("\nNOTE: For the live pipeline use pipeline_read. For live performance use ga_performance / gsc_page_performance.")

    wp_by_id = {str(w.get("wp_id")): w.get("name", "") for w in wp_tax if w.get("wp_id")}
    lm_by_cluster = {(l.get("cluster") or "").strip(): l for l in lms if (l.get("cluster") or "").strip()}
    tax_by_cluster = {c["cluster"]: c for c in clusters if c.get("cluster")}
    all_clusters = sorted(set(lm_by_cluster) | set(tax_by_cluster))
    if all_clusters:
        L.append("\n=== CLUSTER CONTEXT (use when building briefs) ===")
        for cl in all_clusters:
            lm, tax = lm_by_cluster.get(cl, {}), tax_by_cluster.get(cl, {})
            parts = [cl]
            if lm.get("cta_headline"):
                parts.append(f'LM: "{lm["cta_headline"]}"')
            if lm.get("lead_magnet_url"):
                parts.append("CTA-> " + lm["lead_magnet_url"].replace("https://amdigitalke.com", ""))
            cat = str(tax.get("wp_category_id") or "")
            if cat:
                parts.append(f"Cat: {cat} ({wp_by_id.get(cat, cat)})")
            if tax.get("wp_tag_ids"):
                parts.append(f"Tags: {tax['wp_tag_ids']}")
            L.append(" | ".join(parts))
    L.append("=== END CONTEXT ===")

    block = "\n".join(L)
    _ctx_cache.update(block=block, ts=now)
    return block


def _prompt(state):
    return [SystemMessage(content=SYSTEM_PROMPT + "\n\n" + build_context_block())] + state["messages"]


def make_checkpointer():
    if config.DATABASE_URL:
        cp = PostgresSaver.from_conn_string(config.DATABASE_URL).__enter__()  # long-lived
        cp.setup()
        return cp
    return MemorySaver()  # dev fallback — sessions lost on restart


def make_graph(checkpointer):
    model = ChatOpenAI(
        model=config.MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.3,
        max_tokens=config.MAX_TOKENS,
    )
    return create_react_agent(model, ALL_TOOLS, prompt=_prompt, checkpointer=checkpointer)
