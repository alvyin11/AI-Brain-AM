"""The 4 autonomous crons as APScheduler jobs — same prompts, schedules, and
guardrails as the n8n Brain Cron workflows. Reports -> brain_reports + optional Telegram."""
import datetime

import requests
from apscheduler.schedulers.background import BackgroundScheduler

from app import config
from app.tools.db import log_report, rpc

PROMPTS = {
    "watchdog": ("[SCHEDULED] Weekly traffic watchdog. 1) Call ga_performance mode site_summary for the last 7 days, "
                 "then mode top_pages. 2) For any top page whose sessions dropped sharply vs the previous period, call "
                 "gsc_page_performance to diagnose position vs CTR vs impressions. 3) If a drop looks content-related: "
                 "run keyword_research and serp_analysis, add a rewrite brief via pipeline_add (stays Pending Review), "
                 "and create a remember_task to re-check in 14 days. 4) End with a compact report. If nothing dropped, "
                 "say so in 2 lines."),
    "replenish": ("[SCHEDULED] Weekly pipeline replenishment. 1) Call pipeline_read for W1 with status_filter pending. "
                  "2) If 5 or more rows are pending, reply NO ACTION NEEDED with the count and stop. 3) If fewer: call "
                  "cluster_health summary, pick the 2 weakest clusters, and for each find one strong opportunity using "
                  "check_existing_content + pipeline_search + knowledge_search (dedup), keyword_research, serp_analysis. "
                  "4) Add up to 3 rows via pipeline_add with exact cluster names from CLUSTER CONTEXT. 5) Compact report."),
    "outcome": ("[SCHEDULED] Post-publish outcome review. 1) Call content_inventory and ga_performance recent_posts to "
                "find articles published roughly 25-40 days ago. 2) For up to 5, call gsc_page_performance (28 days). "
                "3) Verdict each: WORKING, SLOW, or FAILING, with the likely reason. 4) Call save_learning once per "
                "article with the verdict and a transferable lesson. 5) remember_task for FAILING articles worth a "
                "rewrite. 6) Compact report, one line per article."),
    "tasks": ("[SCHEDULED] Daily task check. 1) Call list_tasks with status_filter due. 2) For each due task, perform "
              "the check it describes using your tools where possible. 3) complete_task only when its check is done. "
              "4) Compact report: each task, finding, done or still open."),
}


def _notify(kind: str, text: str):
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                      json={"chat_id": config.TELEGRAM_CHAT_ID,
                            "text": f"AMDK Brain [{kind}]\n\n{text[:3800]}"}, timeout=15)
    except Exception:
        pass


def _make_job(kind: str, run_brain):
    def job():
        if kind == "tasks":  # pre-check: skip the LLM call when nothing is due
            due = rpc("rpc_task_list", {"p_filter": "due"})
            if isinstance(due, dict) and not due.get("count"):
                return
        session_id = f"cron_{kind}_{datetime.date.today().isoformat()}"
        try:
            report = run_brain(PROMPTS[kind], session_id)
        except Exception as e:
            report = f"CRON FAILED: {e}"
        log_report(kind, report, session_id)
        _notify(kind, report)
    return job


def start_scheduler(run_brain):
    sched = BackgroundScheduler(timezone="Africa/Nairobi")
    sched.add_job(_make_job("replenish", run_brain), "cron", day_of_week="mon", hour=5, minute=30)
    sched.add_job(_make_job("watchdog", run_brain), "cron", day_of_week="tue", hour=6)
    sched.add_job(_make_job("outcome", run_brain), "cron", day_of_week="sun", hour=6)
    sched.add_job(_make_job("tasks", run_brain), "cron", hour=7)
    sched.start()
    return sched
