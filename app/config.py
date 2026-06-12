"""Central config — everything comes from .env (see .env.example)."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Supabase (data layer — same RPC functions the n8n v3.0 brain uses) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dogwxbuxlalrrtpvexmx.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
# Direct Postgres connection (LangGraph checkpointer). If IPv6 fails on the VPS,
# use the Session Pooler URI from the Supabase dashboard instead.
DATABASE_URL = os.getenv("DATABASE_URL", "")

# --- LLM (OpenRouter, same model as the n8n brain) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "anthropic/claude-sonnet-4.6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))

# --- RAG (same Qdrant container + collection as the n8n brain) ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "amdk_knowledge")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # embeddings only

# --- External APIs (identical credentials to the n8n workflows) ---
DATAFORSEO_AUTH = os.getenv("DATAFORSEO_AUTH", "")        # base64 login:password
WP_BASE_URL = os.getenv("WP_BASE_URL", "https://amdigitalke.com/wp-json/wp/v2")
WP_AUTH = os.getenv("WP_AUTH", "")                        # base64 basic auth
LOCATION_CODE = int(os.getenv("LOCATION_CODE", "2404"))
CLIENT_ID = os.getenv("CLIENT_ID", "amdk")

# --- GA4 / GSC (optional until service account provided) ---
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")  # path to json file
GSC_SITE = os.getenv("GSC_SITE", "sc-domain:amdigitalke.com")
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")

# --- Notifications (optional) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Observability ---
# LangSmith: set LANGSMITH_TRACING=true + LANGSMITH_API_KEY in .env and traces appear
# at smith.langchain.com automatically (no code needed).

CONTEXT_CACHE_SECONDS = int(os.getenv("CONTEXT_CACHE_SECONDS", "900"))
