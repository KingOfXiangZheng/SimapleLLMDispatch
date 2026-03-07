"""Scheduling engine — strategy pattern for provider selection."""

from __future__ import annotations
import json
import random
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

import requests as http_client

from models import ProviderDAO, GroupDAO, UsageLogDAO
from rate_limiter import rate_limiter


# ======================== Strategy Pattern ========================

class SelectionStrategy(ABC):
    @abstractmethod
    def select(self, candidates: list[dict], model_key: str) -> dict:
        ...

class WeightedRandomStrategy(SelectionStrategy):
    def select(self, candidates: list[dict], model_key: str) -> dict:
        total = sum(c["provider"]["weight"] for c in candidates)
        r = random.uniform(0, total)
        cumulative = 0
        for c in candidates:
            cumulative += c["provider"]["weight"]
            if r <= cumulative:
                return c
        return candidates[0]

class RoundRobinStrategy(SelectionStrategy):
    _indices: dict[str, int] = {}

    def select(self, candidates: list[dict], model_key: str) -> dict:
        key = model_key or "_global_"
        idx = self._indices.get(key, 0) % len(candidates)
        self._indices[key] = idx + 1
        return candidates[idx]


STRATEGIES: dict[str, SelectionStrategy] = {
    "weighted_random": WeightedRandomStrategy(),
    "round_robin": RoundRobinStrategy(),
}


# ======================== Model Resolution ========================

def parse_selected_models(provider: dict) -> list[dict]:
    """Normalize selected_models to [{model, rpd, rpm}, ...]."""
    sm = provider.get("selected_models", [])
    if not sm:
        return []
    if isinstance(sm[0], str):
        return [{"model": m, "rpd": 0, "rpm": 0} for m in sm]
    return sm


def get_effective_models(provider: dict) -> list[str]:
    sm = provider.get("selected_models")
    # None means the key was never set (legacy) → fall back to all models
    if sm is None:
        return provider.get("models", [])
    # Empty list means user explicitly deselected all
    if not sm:
        return []
    # Normalize and return
    selected = parse_selected_models(provider)
    return [s["model"] for s in selected if s.get("enabled", True) is not False]


def get_model_rpd(provider: dict, model: str) -> int:
    """Per-model RPD. 0 = unlimited."""
    for s in parse_selected_models(provider):
        if s["model"] == model:
            return s.get("rpd", 0) or 0
    return provider.get("max_requests_per_day", 0) or 0


def check_model_quota(provider: dict, model: str) -> bool:
    rpd = get_model_rpd(provider, model)
    if rpd <= 0:
        return True
    used = UsageLogDAO.count_today(provider["id"], model)
    return used < rpd


def get_model_rpm(provider: dict, model: str) -> int:
    """Per-model RPM. 0 = unlimited."""
    for s in parse_selected_models(provider):
        if s["model"] == model:
            return s.get("rpm", 0) or 0
    return 0


def get_model_tpm(provider: dict, model: str) -> int:
    """Per-model TPM. 0 = unlimited."""
    for s in parse_selected_models(provider):
        if s["model"] == model:
            return s.get("tpm", 0) or 0
    return 0


def get_model_total_requests(provider: dict, model: str) -> int:
    """Per-model total requests limit. 0 = unlimited."""
    for s in parse_selected_models(provider):
        if s["model"] == model:
            return s.get("total_requests", 0) or 0
    return 0


def get_model_total_tokens(provider: dict, model: str) -> int:
    """Per-model total tokens limit. 0 = unlimited."""
    for s in parse_selected_models(provider):
        if s["model"] == model:
            return s.get("total_tokens", 0) or 0
    return 0


# ======================== Core Scheduler ========================

class Scheduler:
    @staticmethod
    def reset_quotas():
        ProviderDAO.reset_daily_quotas()

    @staticmethod
    def fetch_models(provider_id: int) -> list[str]:
        provider = ProviderDAO.get_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")
        url = provider["base_url"].rstrip("/") + "/models"
        resp = http_client.get(
            url,
            headers={"Authorization": f"Bearer {provider['api_key']}"},
            timeout=15
        )
        resp.raise_for_status()
        models = [m["id"] for m in resp.json().get("data", [])]
        ProviderDAO.update_models(provider_id, models)
        return models

    @staticmethod
    def resolve_model(model_requested: str | None) -> tuple[list[str], str]:
        """Returns (target_models, strategy_name)."""
        if not model_requested:
            providers = ProviderDAO.get_active()
            all_models = set()
            for p in providers:
                all_models.update(get_effective_models(p))
            return list(all_models), "round_robin"

        group = GroupDAO.get_by_alias(model_requested)
        if group:
            return group["target_models"], group.get("strategy", "round_robin")

        return [model_requested], "round_robin"

    @staticmethod
    def find_available(
        target_models: list[str],
        excluded_ids: set[int] | None = None
    ) -> list[dict]:
        """Returns [{provider, matched_model}, ...]."""
        excluded = excluded_ids or set()
        providers = ProviderDAO.get_active()
        results = []

        for p in providers:
            if p["id"] in excluded:
                continue
            # Provider-level daily quota check RPD
            max_rpd = p.get("max_requests_per_day", 0) or 0
            if max_rpd > 0 and p.get("current_requests_today", 0) >= max_rpd:
                continue
            # Provider-level total requests check
            max_total_req = p.get("max_requests_total", 0) or 0
            if max_total_req > 0 and UsageLogDAO.count_all(p["id"]) >= max_total_req:
                continue
            # Provider-level total tokens check
            max_total_tok = p.get("max_tokens_total", 0) or 0
            if max_total_tok > 0 and UsageLogDAO.sum_tokens(p["id"]) >= max_total_tok:
                continue
            # RPM TPM
            if not rate_limiter.check(p):
                continue
            effective = get_effective_models(p)
            for model in target_models:
                if model not in effective:
                    continue
                #RPD
                if not check_model_quota(p, model):
                    continue
                # Per-model RPM check
                model_rpm = get_model_rpm(p, model)
                if not rate_limiter.check_model_rpm(p["id"], model, model_rpm):
                    continue
                # Per-model TPM check
                model_tpm = get_model_tpm(p, model)
                if not rate_limiter.check_model_tpm(p["id"], model, model_tpm):
                    continue
                # Per-model total requests check
                m_total_req = get_model_total_requests(p, model)
                if m_total_req > 0 and UsageLogDAO.count_all_by_model(p["id"], model) >= m_total_req:
                    continue
                # Per-model total tokens check
                m_total_tok = get_model_total_tokens(p, model)
                if m_total_tok > 0 and UsageLogDAO.sum_tokens_by_model(p["id"], model) >= m_total_tok:
                    continue
                
                # Health check: skip if too many consecutive failures AND in cooldown
                model_info = next((s for s in parse_selected_models(p) if s["model"] == model), None)
                if model_info:
                    # Interval check
                    interval = model_info.get("interval", 0)
                    if interval > 0:
                        last_success_str = model_info.get("last_success_time")
                        if last_success_str:
                            try:
                                last_success = datetime.fromisoformat(last_success_str)
                                if datetime.utcnow() - last_success < timedelta(seconds=interval):
                                    continue # Still in interval wait period
                            except ValueError:
                                pass # Ignore parse errors for interval
                    
                    # Cooldown check
                    if model_info.get("consecutive_failures", 0) >= 3:
                        last_failure_str = model_info.get("last_failure_time")
                        if last_failure_str:
                            try:
                                last_failure = datetime.fromisoformat(last_failure_str)
                                if datetime.utcnow() - last_failure < timedelta(minutes=5):
                                    continue # Still in cooldown
                            except ValueError:
                                continue # Parse error, safer to skip
                        else:
                            continue # No timestamp but high fails, assume disabled
                    
                results.append({"provider": p, "matched_model": model})
        return results

    @staticmethod
    def pick(candidates: list[dict], strategy_name: str, model_key: str | None) -> dict:
        strategy = STRATEGIES.get(strategy_name, STRATEGIES["weighted_random"])
        return strategy.select(candidates, model_key or "_global_")

    @staticmethod
    def record_usage(provider_id: int, model: str, usage: dict | None = None,
                     status_code: int = 200, error_message: str | None = None):
        ProviderDAO.increment_requests(provider_id)
        total = (usage or {}).get("total_tokens", 0)
        if total > 0:
            rate_limiter.record_tokens(provider_id, total)
        UsageLogDAO.insert(provider_id, model, usage, status_code, error_message)
