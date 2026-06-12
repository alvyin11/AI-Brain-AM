"""WordPress REST tools — identical endpoints + auth to the n8n brain."""
import requests
from langchain_core.tools import tool

from app import config


def _get(path: str, params: dict) -> list | dict:
    r = requests.get(f"{config.WP_BASE_URL}/{path}", params=params,
                     headers={"Authorization": f"Basic {config.WP_AUTH}"}, timeout=20)
    if r.status_code >= 300:
        return {"ok": False, "error": f"WP REST HTTP {r.status_code}"}
    return r.json()


@tool
def check_existing_content(search_query: str) -> dict:
    """Search published amdigitalke.com posts for a topic/keyword (live WordPress search).
    ALWAYS call before creating any new post brief."""
    out = _get("posts", {"search": search_query, "status": "publish", "per_page": 5,
                         "_fields": "id,title,link,slug,modified"})
    if isinstance(out, dict):
        return out
    return {"ok": True, "matches": [{"id": p["id"], "title": p["title"]["rendered"],
                                     "url": p["link"], "modified": p["modified"]} for p in out]}


@tool
def get_post_details(post_slug: str) -> dict:
    """Fetch one published post by URL slug — full content, for rewrites and diagnosis."""
    out = _get("posts", {"slug": post_slug, "_fields": "id,title,link,slug,content,modified,excerpt"})
    if isinstance(out, dict):
        return out
    if not out:
        return {"ok": False, "error": f"no post with slug {post_slug}"}
    p = out[0]
    import re
    text = re.sub(r"<[^>]+>", " ", p["content"]["rendered"])
    text = re.sub(r"\s+", " ", text).strip()
    return {"ok": True, "id": p["id"], "title": p["title"]["rendered"], "url": p["link"],
            "modified": p["modified"], "content_text": text[:12000]}


@tool
def get_updated_posts() -> dict:
    """List the 20 most recently modified published posts."""
    out = _get("posts", {"orderby": "modified", "order": "desc", "per_page": 20,
                         "status": "publish", "_fields": "id,title,link,slug,modified"})
    if isinstance(out, dict):
        return out
    return {"ok": True, "posts": [{"title": p["title"]["rendered"], "url": p["link"],
                                   "modified": p["modified"]} for p in out]}
