"""knowledge_search — same Qdrant collection + embedding model as the n8n brain."""
import requests
from langchain_core.tools import tool

from app import config


def _embed(text: str) -> list[float]:
    r = requests.post("https://api.openai.com/v1/embeddings", timeout=30,
                      headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}",
                               "Content-Type": "application/json"},
                      json={"model": "text-embedding-3-small", "input": text})
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


@tool
def knowledge_search(query: str) -> dict:
    """Semantic search over the long-term knowledge base: the 2026 Strategy Brain, Prompt
    Layer task templates, Strategy Audit, every published amdigitalke.com article, and saved
    outcome learnings. ALWAYS call before strategy recommendations or briefs."""
    if not config.OPENAI_API_KEY:
        return {"ok": False, "error": "OPENAI_API_KEY not configured (needed for embeddings)"}
    try:
        vec = _embed(query)
        r = requests.post(f"{config.QDRANT_URL}/collections/{config.QDRANT_COLLECTION}/points/search",
                          json={"vector": vec, "limit": 6, "with_payload": True}, timeout=20)
        r.raise_for_status()
        hits = r.json().get("result", [])
        return {"ok": True, "results": [
            {"score": round(h.get("score", 0), 3),
             "title": (h.get("payload") or {}).get("metadata", {}).get("title")
                      or (h.get("payload") or {}).get("title", ""),
             "url": (h.get("payload") or {}).get("metadata", {}).get("url")
                    or (h.get("payload") or {}).get("url", ""),
             "content": ((h.get("payload") or {}).get("content")
                         or (h.get("payload") or {}).get("page_content", ""))[:1200]}
            for h in hits]}
    except Exception as e:
        return {"ok": False, "error": f"knowledge_search failed: {e}"}
