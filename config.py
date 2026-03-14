import os

PORT = int(os.environ.get("PORT", 3100))
DB_PATH = os.environ.get("DB_PATH", "data/llm_dispatcher.db")
UPSTREAM_TIMEOUT = int(os.environ.get("UPSTREAM_TIMEOUT", 60))
MAX_FAILOVER_ATTEMPTS = 10
DEBUG = 1
Cooldown = 300  # s
ADMIN_KEY = os.environ.get("ADMIN_KEY", "123456")
