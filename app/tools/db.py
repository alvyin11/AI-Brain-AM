"""All Supabase data tools. Every tool = one RPC call to the functions defined in
'n8n and superbase/03-supabase-functions.sql' — the exact same data layer the
n8n v3.0 brain uses, so both brains can run side by side on identical data."""
import json
import requests
from langchain_core.tools import tool

from app import config


def rpc(name: str, args: dict) -> dict | list:
    r = requests.post(
        f"{config.SUPABASE_URL}/rest/v1/rpc/{name}",
        headers={
            "apikey": config.SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(args),
        timeout=20,
    )
    if r.status_code >= 300:
        return {"ok": False, "error": f"supabase {name}: HTTP {r.status_code} {r.text[:300]}"}
    try:
        return r.json()
    except Exception:
        return {"ok": True}


def get_brain_context() -> dict:
    out = rpc("get_brain_context", {"p_client_id": config.CLIENT_ID})
    return out if isinstance(out, dict) else {}


def log_conversation(payload: dict) -> None:
    rpc("rpc_log_conversation", {"p": payload})


def log_report(report_type: str, report: str, session_id: str) -> None:
    rpc("rpc_log_report", {"p": {"report_type": report_type, "report": report, "session_id": session_id}})


# --------------------------------------------------------------------- tools
@tool
def remember_task(task_text: str, due_date: str = "", related_url: str = "") -> dict:
    """Save a follow-up task with a due date (YYYY-MM-DD; empty = 14 days out) so the
    daily task cron checks it later. Use whenever a re-check is promised."""
    return rpc("rpc_task_add", {"p": {"task_text": task_text, "due_date": due_date,
                                      "related_url": related_url, "source": "brain"}})


@tool
def list_tasks(status_filter: str = "due") -> dict:
    """List saved follow-up tasks. status_filter: due (default), open, or all."""
    return rpc("rpc_task_list", {"p_filter": status_filter})


@tool
def complete_task(task_id: str) -> dict:
    """Mark a follow-up task Done by task_id — only after its check was actually done."""
    return rpc("rpc_task_complete", {"p_task_id": task_id})


@tool
def save_learning(learning_text: str, verdict: str = "", url: str = "", target_kw: str = "") -> dict:
    """Record a post-publish outcome lesson (verdict WORKING/SLOW/FAILING). Learnings are
    embedded into the knowledge base weekly and shape future briefs."""
    return rpc("rpc_learning_add", {"p": {"learning_text": learning_text, "verdict": verdict,
                                          "url": url, "target_kw": target_kw}})


@tool
def update_client_notes(notes: str = "", current_strategy: str = "") -> dict:
    """Append a durable note to the client record and optionally update Current_Strategy.
    Call when the user says remember this, note that, or update strategy."""
    return rpc("rpc_client_note", {"p_client_id": config.CLIENT_ID, "p_note": notes,
                                   "p_strategy": current_strategy})


@tool
def update_audit_notes(observation: str) -> dict:
    """Save a manual SEO observation (Screaming Frog / Ahrefs / SE Ranking finding) to the audit data."""
    return rpc("rpc_audit_note", {"p_client_id": config.CLIENT_ID, "p_observation": observation})


@tool
def pipeline_read(pipeline: str = "both", status_filter: str = "all", cluster: str = "") -> dict:
    """Read the live W1 (SEO) / W2 (Thought Leadership) pipelines.
    pipeline: w1, w2, both. status_filter: pending, approved, all. cluster: optional name."""
    return rpc("rpc_pipeline_read", {"p_pipeline": pipeline, "p_status": status_filter, "p_cluster": cluster})


@tool
def pipeline_search(query: str) -> dict:
    """Search W1, W2, and published articles by topic, keyword, or title.
    ALWAYS call before any new brief, alongside check_existing_content and knowledge_search."""
    return rpc("rpc_pipeline_search", {"p_query": query})


@tool
def pipeline_add(pipeline: str, article_title: str, primary_keyword: str = "", cluster: str = "",
                 content_type: str = "", rationale: str = "", kenya_variant: str = "",
                 search_volume_est: str = "", track: str = "", priority: str = "",
                 sub_type: str = "", competitor_reference: str = "") -> dict:
    """Add a NEW article row to w1 or w2 (lands as Pending Review — never publishes directly).
    Confirm the cluster with the user first. W1 also takes track + priority; W2 takes
    sub_type + competitor_reference."""
    return rpc("rpc_pipeline_add", {"p": {
        "pipeline": pipeline, "article_title": article_title, "primary_keyword": primary_keyword,
        "cluster": cluster, "content_type": content_type, "rationale": rationale,
        "kenya_variant": kenya_variant, "search_volume_est": search_volume_est,
        "track": track, "priority": priority, "sub_type": sub_type,
        "competitor_reference": competitor_reference}})


@tool
def pipeline_update_notes(pipeline: str, row_id: str, notes_text: str) -> dict:
    """Save a brief or notes to an existing pipeline row (Notes on W2, Rationale on W1).
    Confirm row_id and pipeline with the user first."""
    return rpc("rpc_pipeline_update_notes", {"p_pipeline": pipeline, "p_row_id": row_id, "p_notes": notes_text})


@tool
def pipeline_approve(pipeline: str, row_id: str, mode: str = "approve", distribution_link: str = "") -> dict:
    """Approve a pipeline row. mode=approve sets Draft_Status Approved (W1/W2 writes the
    article); mode=approve_distribution sets Distribution_Link + Distribute Approved on W2.
    ONLY call after the user explicitly typed APPROVE/go ahead AND confirmed the row_id."""
    return rpc("rpc_pipeline_approve", {"p_mode": mode, "p_pipeline": pipeline,
                                        "p_row_id": row_id, "p_distribution_link": distribution_link})


@tool
def content_inventory(cluster: str = "", source: str = "", content_type: str = "") -> dict:
    """Browse all published articles. Optional filters: cluster, source (W1/W2/EXISTING), content_type."""
    return rpc("rpc_content_inventory", {"p_cluster": cluster, "p_source": source, "p_content_type": content_type})


@tool
def linking_backlog(cluster: str = "") -> dict:
    """Articles waiting for internal links, oldest first. Optional cluster filter."""
    return rpc("rpc_linking_backlog", {"p_cluster": cluster})


@tool
def cluster_health(mode: str = "summary", cluster: str = "") -> dict:
    """Cluster health: published count, W1/W2 queue depth, linking backlog per cluster.
    mode=summary for all clusters, mode=detail with a cluster name for one."""
    return rpc("rpc_cluster_health", {"p_mode": mode, "p_cluster": cluster})


@tool
def save_to_pipeline(brief_json: str) -> dict:
    """Save a CROSS-CLIENT audit/research brief (NOT AM Digital KE content — use pipeline_add
    for that). Only after explicit APPROVE. brief_json: JSON string with post_type, title,
    target_kw, kw_volume, kd_score, secondary_kws, h2_outline, word_count_target, notes."""
    return rpc("rpc_save_brief", {"p": {"client_id": config.CLIENT_ID, "brief_json": brief_json}})
