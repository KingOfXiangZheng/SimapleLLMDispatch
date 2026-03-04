import os

PORT = int(os.environ.get("PORT", 3000))
DB_PATH = os.environ.get("DB_PATH", "data/llm_dispatcher.db")
UPSTREAM_TIMEOUT = int(os.environ.get("UPSTREAM_TIMEOUT", 30))
MAX_FAILOVER_ATTEMPTS = 2
