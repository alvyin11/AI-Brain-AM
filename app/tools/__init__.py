"""Tool registry — 23 tools (the n8n brain's 26 minus pipeline_audit (Phase B),
monthly_digest (Phase B PDF job), read_research_file (Drive — Phase B))."""
from app.tools.db import (remember_task, list_tasks, complete_task, save_learning,
                          update_client_notes, update_audit_notes, pipeline_read,
                          pipeline_search, pipeline_add, pipeline_update_notes,
                          pipeline_approve, content_inventory, linking_backlog,
                          cluster_health, save_to_pipeline)
from app.tools.wp import check_existing_content, get_post_details, get_updated_posts
from app.tools.dataforseo import keyword_research, serp_analysis
from app.tools.rag import knowledge_search
from app.tools.analytics import gsc_page_performance, ga_performance

ALL_TOOLS = [
    # research + dedup
    check_existing_content, pipeline_search, knowledge_search, keyword_research, serp_analysis,
    # content + performance
    get_post_details, get_updated_posts, content_inventory, linking_backlog, cluster_health,
    gsc_page_performance, ga_performance,
    # pipeline writes
    pipeline_read, pipeline_add, pipeline_update_notes, pipeline_approve, save_to_pipeline,
    # memory
    remember_task, list_tasks, complete_task, save_learning, update_client_notes, update_audit_notes,
]
