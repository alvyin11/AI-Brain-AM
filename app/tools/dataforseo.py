"""DataforSEO tools — same API + credentials as the n8n subworkflows.
PARITY NOTE: compare one output against the n8n keyword_research / serp_analysis
subworkflow during Session 6 validation; adjust endpoint/params if they differ."""
import requests
from langchain_core.tools import tool

from app import config

BASE = "https://api.dataforseo.com"


def _post(path: str, payload: list) -> dict:
    r = requests.post(BASE + path, json=payload, timeout=60,
                      headers={"Authorization": f"Basic {config.DATAFORSEO_AUTH}",
                               "Content-Type": "application/json"})
    if r.status_code >= 300:
        return {"ok": False, "error": f"DataforSEO HTTP {r.status_code}"}
    return r.json()


@tool
def keyword_research(keywords: str) -> dict:
    """Get Google search volume, competition, and CPC for up to 5 comma-separated keywords
    in Kenya (location 2404). ALWAYS call before recommending any keyword."""
    kws = [k.strip() for k in keywords.split(",") if k.strip()][:5]
    out = _post("/v3/keywords_data/google_ads/search_volume/live",
                [{"keywords": kws, "location_code": config.LOCATION_CODE, "language_code": "en"}])
    if not out.get("tasks"):
        return {"ok": False, "error": str(out)[:300]}
    results = []
    for item in (out["tasks"][0].get("result") or []):
        results.append({"keyword": item.get("keyword"), "volume": item.get("search_volume"),
                        "competition": item.get("competition"), "cpc": item.get("cpc")})
    return {"ok": True, "keywords": results}


@tool
def serp_analysis(keyword: str) -> dict:
    """Top 10 Google results for a keyword in Kenya — what competitors cover, content gaps,
    word-count benchmarks. Call when building any brief."""
    out = _post("/v3/serp/google/organic/live/advanced",
                [{"keyword": keyword, "location_code": config.LOCATION_CODE,
                  "language_code": "en", "depth": 10}])
    if not out.get("tasks"):
        return {"ok": False, "error": str(out)[:300]}
    items = []
    for res in (out["tasks"][0].get("result") or []):
        for it in (res.get("items") or []):
            if it.get("type") == "organic" and len(items) < 10:
                items.append({"position": it.get("rank_absolute"), "title": it.get("title"),
                              "url": it.get("url"), "description": (it.get("description") or "")[:200]})
    return {"ok": True, "keyword": keyword, "top10": items}
