"""OpenAI-compatible proxy routes."""

from flask import Blueprint, request, jsonify, Response, stream_with_context
import requests as http_client

from config import UPSTREAM_TIMEOUT, MAX_FAILOVER_ATTEMPTS
from scheduler import Scheduler, get_effective_models
from models import ProviderDAO, GroupDAO

proxy_bp = Blueprint("proxy", __name__)


@proxy_bp.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    Scheduler.reset_quotas()
    return _handle_chat(request.json, attempt=0, excluded_ids=set())


@proxy_bp.route("/v1/models", methods=["GET"])
def list_models():
    providers = ProviderDAO.get_active()
    all_models = set()
    for p in providers:
        all_models.update(get_effective_models(p))

    groups = GroupDAO.get_all()
    for g in groups:
        all_models.add(g["alias"])

    return jsonify({
        "object": "list",
        "data": [{"id": m, "object": "model"} for m in sorted(all_models)]
    })


def _handle_chat(body: dict, attempt: int, excluded_ids: set):
    model_requested = body.get("model")
    target_models, strategy = Scheduler.resolve_model(model_requested)
    candidates = Scheduler.find_available(target_models, excluded_ids)

    if not candidates:
        return jsonify({"error": "No provider found or quota exceeded"}), 404

    picked = Scheduler.pick(candidates, strategy, model_requested)
    provider = picked["provider"]
    actual_model = picked["matched_model"]

    url = provider["base_url"].rstrip("/") + "/chat/completions"
    headers = {
        "lora_id":"0",
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    upstream_body = {**body, "model": actual_model}

    try:
        if body.get("stream"):
            return _handle_stream(url, headers, upstream_body, provider, actual_model)
        else:
            return _handle_normal(url, headers, upstream_body, provider, actual_model)
    except Exception as e:
        print(f"Provider {provider['name']} failed: {e}")
        ProviderDAO.record_model_failure(provider["id"], actual_model)
        if attempt < MAX_FAILOVER_ATTEMPTS and len(candidates) > 1:
            excluded_ids.add(provider["id"])
            return _handle_chat(body, attempt + 1, excluded_ids)
        return jsonify({"error": str(e)}), 500


def _handle_normal(url, headers, body, provider, model):
    resp = http_client.post(url, json=body, headers=headers, timeout=UPSTREAM_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    ProviderDAO.record_model_success(provider["id"], model)
    Scheduler.record_usage(provider["id"], model, data.get("usage"))
    return jsonify(data), resp.status_code


def _handle_stream(url, headers, body, provider, model):
    # Request usage in final chunk (OpenAI-compatible)
    body["stream_options"] = {"include_usage": True}
    resp = http_client.post(
        url, json=body, headers=headers,
        timeout=UPSTREAM_TIMEOUT, stream=True
    )

    stream_usage = {}

    def generate():
        nonlocal stream_usage
        try:
            buffer = ""
            for chunk in resp.iter_content(chunk_size=None):
                if chunk:
                    text = chunk.decode("utf-8", errors="replace")
                    buffer += text
                    # Parse complete SSE lines for usage
                    lines = buffer.split("\n")
                    buffer = lines[-1]  # keep incomplete line
                    for line in lines[:-1]:
                        if line.startswith("data:") and line.strip() != "data: [DONE]":

                            try:
                                import json
                                parsed = json.loads(line[5:])
                                if parsed.get("usage"):
                                    stream_usage = parsed["usage"]
                            except Exception:
                                pass
                    yield chunk
            # Check remaining buffer
            if buffer:
                for line in buffer.split("\n"):
                    if line.startswith("data:") and line.strip() != "data: [DONE]":

                        try:
                            import json
                            parsed = json.loads(line[5:])
                            if parsed.get("usage"):
                                stream_usage = parsed["usage"]
                        except Exception:
                            pass
        finally:
            if stream_usage:
                ProviderDAO.record_model_success(provider["id"], model)
            Scheduler.record_usage(provider["id"], model, stream_usage or None)

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
