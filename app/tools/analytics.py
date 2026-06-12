"""GSC + GA4 tools. GSC works once a Google service-account JSON is provided
(add the service account email as a user in Search Console). GA4 likewise.
Until then both return a clear 'not configured' message — the agent's prompt
tells it to say which lookup is unavailable instead of inventing numbers."""
import datetime as dt
from langchain_core.tools import tool

from app import config


def _gsc_client():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


@tool
def gsc_page_performance(url_slug: str, days: int = 28) -> dict:
    """Google Search Console data for one page: clicks, impressions, CTR, average position,
    and top queries. Input: page slug or full URL."""
    if not config.GOOGLE_SERVICE_ACCOUNT_JSON:
        return {"ok": False, "error": "GSC not configured yet — GOOGLE_SERVICE_ACCOUNT_JSON missing. Tell the user this lookup is unavailable."}
    try:
        page = url_slug if url_slug.startswith("http") else f"https://amdigitalke.com/{url_slug.strip('/')}/"
        end = dt.date.today().isoformat()
        start = (dt.date.today() - dt.timedelta(days=days)).isoformat()
        svc = _gsc_client()
        body = {"startDate": start, "endDate": end, "dimensions": ["query"], "rowLimit": 10,
                "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "equals", "expression": page}]}]}
        rows = svc.searchanalytics().query(siteUrl=config.GSC_SITE, body=body).execute().get("rows", [])
        totals = {"clicks": sum(r["clicks"] for r in rows), "impressions": sum(r["impressions"] for r in rows)}
        return {"ok": True, "page": page, "days": days, **totals,
                "top_queries": [{"query": r["keys"][0], "clicks": r["clicks"],
                                 "position": round(r["position"], 1)} for r in rows]}
    except Exception as e:
        return {"ok": False, "error": f"GSC lookup failed: {e}"}


@tool
def ga_performance(mode: str = "site_summary", url_slug: str = "", days: int = 28) -> dict:
    """GA4 traffic data. Modes: site_summary, top_pages, page_performance (pass url_slug),
    traffic_sources, recent_posts."""
    if not config.GA4_PROPERTY_ID or not config.GOOGLE_SERVICE_ACCOUNT_JSON:
        return {"ok": False, "error": "GA4 not configured yet — GA4_PROPERTY_ID / service account missing. Tell the user this lookup is unavailable."}
    try:
        from google.oauth2 import service_account
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
        creds = service_account.Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        client = BetaAnalyticsDataClient(credentials=creds)
        date_range = DateRange(start_date=f"{days}daysAgo", end_date="today")
        if mode == "top_pages" or mode == "recent_posts":
            req = RunReportRequest(property=f"properties/{config.GA4_PROPERTY_ID}", date_ranges=[date_range],
                                   dimensions=[Dimension(name="pagePath")], metrics=[Metric(name="sessions")], limit=10)
        elif mode == "traffic_sources":
            req = RunReportRequest(property=f"properties/{config.GA4_PROPERTY_ID}", date_ranges=[date_range],
                                   dimensions=[Dimension(name="sessionDefaultChannelGroup")],
                                   metrics=[Metric(name="sessions")], limit=10)
        else:
            req = RunReportRequest(property=f"properties/{config.GA4_PROPERTY_ID}", date_ranges=[date_range],
                                   metrics=[Metric(name="sessions"), Metric(name="engagedSessions")])
        resp = client.run_report(req)
        rows = [{"dims": [d.value for d in r.dimension_values],
                 "metrics": [m.value for m in r.metric_values]} for r in resp.rows]
        return {"ok": True, "mode": mode, "days": days, "rows": rows}
    except Exception as e:
        return {"ok": False, "error": f"GA4 lookup failed: {e}"}
