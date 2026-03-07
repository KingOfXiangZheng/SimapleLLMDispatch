"""OpenAI-compatible proxy routes."""

from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
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
        status_code = getattr(e, 'response', None)
        sc = status_code.status_code if status_code else 500
        error_msg = str(e)
        
        ProviderDAO.record_model_failure(provider["id"], actual_model)
        Scheduler.record_usage(provider["id"], actual_model, status_code=sc, error_message=error_msg)
        
        #excluded_ids.add(provider["id"])

        if attempt < MAX_FAILOVER_ATTEMPTS:
            print(f"Retrying failover (attempt {attempt+1})...excluded_ids {excluded_ids}")
            return _handle_chat(body, attempt + 1, excluded_ids)
            
        return jsonify({
            "error": f"All fallback attempts failed. Last error from {provider['name']}: {error_msg}",
            "failed_providers": list(excluded_ids)
        }), sc


def _handle_normal(url, headers, body, provider, model):
    resp = http_client.post(url, json=body, headers=headers, timeout=UPSTREAM_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    ProviderDAO.record_model_success(provider["id"], model)
    Scheduler.record_usage(provider["id"], model, data.get("usage"), status_code=200)
    return jsonify(data), resp.status_code


def _handle_stream(url, headers, body, provider, model):
    # Request usage in final chunk (OpenAI-compatible)
    body["stream_options"] = {"include_usage": True}
    resp = http_client.post(
        url, json=body, headers=headers,
        timeout=UPSTREAM_TIMEOUT, stream=True
    )
    resp.raise_for_status()

    stream_usage = {}

    # Pre-fetch first chunk to catch early errors (like ReadTimeout) for failover
    it = resp.iter_content(chunk_size=None)
    try:
        first_chunk = next(it)
        if first_chunk:
            # Check for silent failures (200 OK but error/abort in payload)
            text = first_chunk.decode("utf-8", errors="replace")
            for line in text.split("\n"):
                if line.startswith("data:") and line.strip() != "data: [DONE]":
                    try:
                        parsed = json.loads(line[5:])
                        # Check choices for finish_reason: abort
                        choices = parsed.get("choices", [])
                        if choices and choices[0].get("finish_reason") == "abort":
                            raise RuntimeError(f"Provider returned abort: {line[5:]}")
                        # Check for top-level or choice-level error
                        if parsed.get("error") or (choices and choices[0].get("delta", {}).get("error")):
                            raise RuntimeError(f"Provider returned error in stream: {line[5:]}")
                    except (json.JSONDecodeError, KeyError):
                        pass

    except StopIteration:
        first_chunk = None
        raise RuntimeError("Provider returned an empty response body.")
    except Exception as e:
        # Re-raise so _handle_chat can catch it and perform failover
        raise e

    def generate():
        nonlocal stream_usage
        try:
            if first_chunk:
                yield first_chunk

            buffer = ""
            # Helper to parse chunks
            def process_text(chunk_data):
                nonlocal stream_usage, buffer
                text = chunk_data.decode("utf-8", errors="replace")
                buffer += text
                lines = buffer.split("\n")
                buffer = lines[-1]
                for line in lines[:-1]:
                    if line.startswith("data:") and line.strip() != "data: [DONE]":
                        try:
                            import json
                            parsed = json.loads(line[5:])
                            if parsed.get("usage"):
                                stream_usage = parsed["usage"]
                        except Exception:
                            pass

            if first_chunk:
                process_text(first_chunk)

            for chunk in it:
                if chunk:
                    process_text(chunk)
                    yield chunk
            
            # Final buffer check
            if buffer:
                for line in buffer.split("\n"):
                    if line.startswith("data:") and line.strip() != "data: [DONE]":
                        try:
                            parsed = json.loads(line[5:])
                            if parsed.get("usage"):
                                stream_usage = parsed["usage"]
                        except Exception:
                            pass
        except Exception as e:
            # Error during streaming - record failure but cannot failover here (headers already sent)
            print(f"Error during streaming from {provider['name']}: {e}")
            sc = getattr(getattr(e, 'response', None), 'status_code', 500)
            ProviderDAO.record_model_failure(provider["id"], model)
            Scheduler.record_usage(provider["id"], model, status_code=sc, error_message=f"Stream Error: {str(e)}")
            # Optionally yield an error chunk for the client
            yield f"\n\ndata: {{\"error\": {json.dumps(str(e))}}}\n\n".encode("utf-8")
        finally:
            if stream_usage:
                ProviderDAO.record_model_success(provider["id"], model)
                Scheduler.record_usage(provider["id"], model, stream_usage, status_code=200)
            elif not first_chunk and not buffer:
                # If nothing was sent, it might be an empty success or silent failure handled elsewhere
                pass

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
