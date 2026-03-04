"""Rate limiter — RPM from DB (persisted), TPM in-memory sliding window."""

import time
from threading import Lock
from models import UsageLogDAO


class RateLimiter:
    """RPM checks query usage_logs (persisted). TPM uses in-memory sliding window."""

    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        # TPM only — in-memory: {provider_id: [{ts, count}, ...]}
        self._tpm_data: dict[int, list] = {}
        self._lock = Lock()

    def _prune_tpm(self, pid: int):
        cutoff = time.time() - self._window
        if pid in self._tpm_data:
            self._tpm_data[pid] = [e for e in self._tpm_data[pid] if e["ts"] > cutoff]

    def check(self, provider: dict) -> bool:
        """Check provider-level RPM (from DB) and TPM (in-memory)."""
        pid = provider["id"]
        max_rpm = provider.get("max_rpm", 0) or 0
        max_tpm = provider.get("max_tpm", 0) or 0

        if max_rpm > 0:
            current = UsageLogDAO.count_last_minute(pid)
            if current >= max_rpm:
                return False

        if max_tpm > 0:
            with self._lock:
                self._prune_tpm(pid)
                total = sum(e["count"] for e in self._tpm_data.get(pid, []))
                if total >= max_tpm:
                    return False
        return True

    def check_model_rpm(self, pid: int, model: str, max_rpm: int) -> bool:
        """Check per-model RPM from DB."""
        if max_rpm <= 0:
            return True
        current = UsageLogDAO.count_last_minute_by_model(pid, model)
        return current < max_rpm

    def check_model_tpm(self, pid: int, model: str, max_tpm: int) -> bool:
        """Check per-model TPM from DB."""
        if max_tpm <= 0:
            return True
        current = UsageLogDAO.sum_tokens_last_minute_by_model(pid, model)
        return current < max_tpm

    def get_model_tpm_current(self, pid: int, model: str) -> int:
        """Current per-model TPM from DB."""
        return UsageLogDAO.sum_tokens_last_minute_by_model(pid, model)

    def get_provider_rpm_current(self, pid: int) -> int:
        """Current provider RPM from DB."""
        return UsageLogDAO.count_last_minute(pid)

    def get_model_rpm_current(self, pid: int, model: str) -> int:
        """Current per-model RPM from DB."""
        return UsageLogDAO.count_last_minute_by_model(pid, model)

    def get_provider_tpm_current(self, pid: int) -> int:
        """Current provider TPM from in-memory sliding window."""
        with self._lock:
            self._prune_tpm(pid)
            return sum(e["count"] for e in self._tpm_data.get(pid, []))

    def record_tokens(self, pid: int, count: int):
        """Record tokens in-memory for TPM tracking."""
        if count > 0:
            with self._lock:
                if pid not in self._tpm_data:
                    self._tpm_data[pid] = []
                self._tpm_data[pid].append({"ts": time.time(), "count": count})


# Singleton
rate_limiter = RateLimiter()
