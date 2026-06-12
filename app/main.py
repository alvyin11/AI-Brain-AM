"""FastAPI entrypoint. Accepts BOTH webhook shapes so the chat UI needs zero changes:
  {"sessionId": "...", "chatInput": "..."}   (chat UI shape)
  {"message": "...", "session_id": "..."}    (n8n brain shape / crons)
Response is a superset of both: {"output", "response", "session_id", "timestamp"}.
Run: uvicorn app.main:app --host 0.0.0.0 --port 8001"""
import datetime
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

from app import config
from app.graph import make_checkpointer, make_graph, build_context_block, _ctx_cache
from app.tools.db import log_conversation
from app.scheduler import start_scheduler

app = FastAPI(title="AM Digital KE — AI Brain (LangGraph)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

checkpointer = make_checkpointer()
graph = make_graph(checkpointer)


@app.on_event("startup")
def _startup():
    start_scheduler(run_brain)


def run_brain(message: str, session_id: str) -> str:
    if re.search(r"\brefresh\b.*\b(context|brain)\b", message, re.I):
        _ctx_cache["ts"] = 0.0
        build_context_block(force=True)
    result = graph.invoke({"messages": [HumanMessage(content=message)]},
                          config={"configurable": {"thread_id": session_id},
                                  "recursion_limit": 40})
    msgs = result["messages"]
    output = msgs[-1].content if msgs else ""
    if isinstance(output, list):  # anthropic content blocks
        output = " ".join(b.get("text", "") for b in output if isinstance(b, dict))
    tools_used = sorted({m.name for m in msgs if getattr(m, "type", "") == "tool" and getattr(m, "name", "")})
    try:
        log_conversation({
            "session_id": session_id, "ts": datetime.datetime.utcnow().isoformat(),
            "client_id": config.CLIENT_ID, "intent_type": "agent_response",
            "user_message": message[:2000],
            "brain_response_summary": output[:800],
            "brief_approved": "Y" if "approve" in message.lower() else "",
            "dataforseo_called": "Y" if {"keyword_research", "serp_analysis"} & set(tools_used) else "",
            "gsc_called": "Y" if {"gsc_page_performance", "ga_performance"} & set(tools_used) else "",
            "wp_post_fetched": "Y" if {"get_post_details", "get_updated_posts", "check_existing_content"} & set(tools_used) else "",
            "notes": ("tools: " + ", ".join(tools_used)) if tools_used else "",
        })
    except Exception:
        pass  # logging must never break a reply
    return output


@app.post("/brain")
@app.post("/webhook/amdk-brain")
async def brain(payload: dict):
    message = (payload.get("chatInput") or payload.get("message") or
               (payload.get("body") or {}).get("message") or "").strip()
    session_id = (payload.get("sessionId") or payload.get("session_id") or
                  f"amdk_{int(time.time())}_{uuid.uuid4().hex[:8]}")
    if not message:
        return {"output": "No message provided.", "response": "No message provided.",
                "session_id": session_id, "error": True}
    output = run_brain(message, session_id)
    return {"output": output, "response": output, "session_id": session_id,
            "timestamp": datetime.datetime.utcnow().isoformat()}


@app.get("/health")
async def health():
    return {"ok": True, "model": config.MODEL}
