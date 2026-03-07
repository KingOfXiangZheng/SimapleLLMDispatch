"""Admin API routes for providers, groups, and logs."""

from flask import Blueprint, request, jsonify
from models import ProviderDAO, GroupDAO, UsageLogDAO
from scheduler import Scheduler, parse_selected_models, get_effective_models, get_model_rpm, get_model_tpm, get_model_total_requests, get_model_total_tokens
from rate_limiter import rate_limiter as _rate_limiter

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _auto_sync_provider_group(name: str, selected_models):
    """Auto-create/update a model_group whose alias = provider name."""
    model_names = []
    if selected_models:
        if isinstance(selected_models[0], str):
            model_names = selected_models
        else:
            model_names = [s["model"] for s in selected_models]
    existing = GroupDAO.get_by_alias(name)
    if existing:
        GroupDAO.update(existing["id"], {
            "name": name, "alias": name,
            "target_models": model_names,
            "strategy": existing.get("strategy", "weighted_random")
        })
    else:
        GroupDAO.create({
            "name": name, "alias": name,
            "target_models": model_names,
            "strategy": "weighted_random"
        })


# ==================== Providers ====================

@admin_bp.route("/providers", methods=["GET"])
def list_providers():
    page = request.args.get("page", 0, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    name = request.args.get("name", "", type=str).strip()
    if page > 0:
        return jsonify(ProviderDAO.get_page(page, page_size, name))
    return jsonify(ProviderDAO.get_all())


@admin_bp.route("/providers/stats", methods=["GET"])
def get_provider_stats():
    """Return aggregate stats for providers."""
    providers = ProviderDAO.get_all()
    total = len(providers)
    active = sum(1 for p in providers if p.get("is_active"))
    today_requests = sum(p.get("current_requests_today", 0) for p in providers)
    
    model_set = set()
    for p in providers:
        # Use selected_models if available, otherwise models
        models = p.get("selected_models") or p.get("models") or []
        for m in models:
            if isinstance(m, dict):
                model_set.add(m["model"])
            else:
                model_set.add(m)
    
    return jsonify({
        "total": total,
        "active": active,
        "today_requests": today_requests,
        "total_models": len(model_set)
    })


@admin_bp.route("/models", methods=["GET"])
def list_all_models():
    """Return all unique model names from all providers (union of models field)."""
    providers = ProviderDAO.get_all()
    model_set = set()
    for p in providers:
        if(p.get("is_active")):
            for m in (p.get("selected_models") or []):
                model_set.add(m["model"])
    return jsonify(sorted(model_set))


@admin_bp.route("/providers", methods=["POST"])
def create_provider():
    try:
        data = request.json
        ProviderDAO.create(data)
        _auto_sync_provider_group(data["name"], data.get("selected_models", data.get("models", [])))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/providers/<int:pid>", methods=["PUT"])
def update_provider(pid):
    try:
        data = request.json
        # Get old name for group rename
        old = ProviderDAO.get_by_id(pid)
        if old and old["name"] != data["name"]:
            old_group = GroupDAO.get_by_alias(old["name"])
            if old_group:
                GroupDAO.delete(old_group["id"])
        ProviderDAO.update(pid, data)
        _auto_sync_provider_group(data["name"], data.get("selected_models", []))
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/providers/<int:pid>", methods=["DELETE"])
def delete_provider(pid):
    try:
        # Clean up auto-created group
        p = ProviderDAO.get_by_id(pid)
        if p:
            g = GroupDAO.get_by_alias(p["name"])
            if g:
                GroupDAO.delete(g["id"])
        ProviderDAO.delete(pid)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/providers/<int:pid>/fetch-models", methods=["POST"])
def fetch_models(pid):
    try:
        models = Scheduler.fetch_models(pid)
        return jsonify({"status": "success", "models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/providers/<int:pid>/reset-health", methods=["POST"])
def reset_provider_health(pid):
    try:
        ProviderDAO.reset_health(pid)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/providers/<int:pid>/quota", methods=["GET"])
def provider_quota(pid):
    try:
        provider = ProviderDAO.get_by_id(pid)
        if not provider:
            return jsonify({"error": "Provider not found"}), 404
        models = get_effective_models(provider)
        parsed = parse_selected_models(provider)
        detail = []
        for m in models:
            entry = next((s for s in parsed if s["model"] == m), None)
            rpd = (entry.get("rpd", 0) or 0) if entry else 0
            if not rpd:
                rpd = provider.get("max_requests_per_day", 0) or 0
            rpm = get_model_rpm(provider, m)
            tpm = get_model_tpm(provider, m)
            total_requests = get_model_total_requests(provider, m)
            total_tokens = get_model_total_tokens(provider, m)
            used = UsageLogDAO.count_today(provider["id"], m)
            rpm_current = _rate_limiter.get_model_rpm_current(provider["id"], m)
            tpm_current = _rate_limiter.get_model_tpm_current(provider["id"], m)
            total_requests_current = UsageLogDAO.count_all_by_model(provider["id"], m)
            total_tokens_current = UsageLogDAO.sum_tokens_by_model(provider["id"], m)
            detail.append({
                "model": m,
                "rpd": rpd, "used_today": used,
                "rpm": rpm, "rpm_current": rpm_current,
                "tpm": tpm, "tpm_current": tpm_current,
                "total_requests": total_requests, "total_requests_current": total_requests_current,
                "interval": (entry.get("interval", 0) or 0) if entry else 0,
                "cooldown": (entry.get("cooldown", 300) or 300) if entry else 300,
                "consecutive_failures": entry.get("consecutive_failures", 0) if entry else 0,
                "last_failure_time": entry.get("last_failure_time") if entry else None,
                "last_success_time": entry.get("last_success_time") if entry else None,
                "enabled": (entry.get("enabled", True) is not False) if entry else True,
            })
        provider_rpm = provider.get("max_rpm", 0) or 0
        provider_rpm_current = _rate_limiter.get_provider_rpm_current(provider["id"])
        provider_tpm = provider.get("max_tpm", 0) or 0
        provider_tpm_current = _rate_limiter.get_provider_tpm_current(provider["id"])
        provider_total_req = provider.get("max_requests_total", 0) or 0
        provider_total_req_current = UsageLogDAO.count_all(provider["id"])
        provider_total_tok = provider.get("max_tokens_total", 0) or 0
        provider_total_tok_current = UsageLogDAO.sum_tokens(provider["id"])
        return jsonify({
            "provider_rpm": provider_rpm,
            "provider_rpm_current": provider_rpm_current,
            "provider_tpm": provider_tpm,
            "provider_tpm_current": provider_tpm_current,
            "provider_total_requests": provider_total_req,
            "provider_total_requests_current": provider_total_req_current,
            "provider_total_tokens": provider_total_tok,
            "provider_total_tokens_current": provider_total_tok_current,
            "models": detail,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Groups ====================

@admin_bp.route("/groups", methods=["GET"])
def list_groups():
    page = request.args.get("page", 0, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    name = request.args.get("name", "", type=str).strip()
    if page > 0:
        return jsonify(GroupDAO.get_page(page, page_size, name))
    return jsonify(GroupDAO.get_all())


@admin_bp.route("/groups", methods=["POST"])
def create_group():
    try:
        GroupDAO.create(request.json)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/groups/<int:gid>", methods=["PUT"])
def update_group(gid):
    try:
        GroupDAO.update(gid, request.json)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/groups/<int:gid>", methods=["DELETE"])
def delete_group(gid):
    try:
        GroupDAO.delete(gid)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ==================== Logs ====================

@admin_bp.route("/logs", methods=["GET"])
def list_logs():
    page = request.args.get("page", 0, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    provider_name = request.args.get("provider_name", "", type=str).strip()
    model = request.args.get("model", "", type=str).strip()
    only_errors = request.args.get("only_errors") == "1"
    
    if page > 0:
        return jsonify(UsageLogDAO.get_page(page, page_size, provider_name, model, only_errors))
    # Legacy: no page param → return flat array
    limit = request.args.get("limit", 100, type=int)
    return jsonify(UsageLogDAO.get_recent(limit))
