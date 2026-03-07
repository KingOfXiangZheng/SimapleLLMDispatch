"""Data Access Objects — thin wrappers around DB operations."""

import json
from datetime import datetime
from database import get_db


class ProviderDAO:
    @staticmethod
    def get_all() -> list[dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM providers").fetchall()
        conn.close()
        return [ProviderDAO._parse(r) for r in rows]

    @staticmethod
    def get_page(page: int = 1, page_size: int = 20, name: str = "") -> dict:
        conn = get_db()
        where_clauses = []
        params = []
        if name:
            where_clauses.append("name LIKE ?")
            params.append(f"%{name}%")
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        total = conn.execute(f"SELECT COUNT(*) as cnt FROM providers{where_sql}", params).fetchone()["cnt"]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM providers{where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()
        conn.close()
        return {
            "items": [ProviderDAO._parse(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    @staticmethod
    def get_active() -> list[dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM providers WHERE is_active = 1").fetchall()
        conn.close()
        return [ProviderDAO._parse(r) for r in rows]

    @staticmethod
    def get_by_id(pid: int) -> dict | None:
        conn = get_db()
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (pid,)).fetchone()
        conn.close()
        return ProviderDAO._parse(row) if row else None

    @staticmethod
    def create(data: dict):
        conn = get_db()
        conn.execute(
            """INSERT INTO providers
               (name, base_url, api_key, models, selected_models, weight, max_requests_per_day, max_rpm, max_tpm, max_requests_total, max_tokens_total)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (data["name"], data["base_url"], data["api_key"],
             json.dumps(data.get("models", [])),
             json.dumps(data.get("selected_models", data.get("models", []))),
             data.get("weight", 1),
             data.get("max_requests_per_day", 1000),
             data.get("max_rpm", 0),
             data.get("max_tpm", 0),
             data.get("max_requests_total", 0),
             data.get("max_tokens_total", 0))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update(pid: int, data: dict):
        conn = get_db()
        conn.execute(
            """UPDATE providers
               SET name=?, base_url=?, api_key=?, models=?, selected_models=?,
                   weight=?, max_requests_per_day=?, max_rpm=?, max_tpm=?,
                   max_requests_total=?, max_tokens_total=?, is_active=?
               WHERE id=?""",
            (data["name"], data["base_url"], data["api_key"],
             json.dumps(data.get("models", [])),
             json.dumps(data.get("selected_models", [])),
             data.get("weight", 1),
             data.get("max_requests_per_day", 1000),
             data.get("max_rpm", 0),
             data.get("max_tpm", 0),
             data.get("max_requests_total", 0),
             data.get("max_tokens_total", 0),
             1 if data.get("is_active", True) else 0,
             pid)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def delete(pid: int):
        conn = get_db()
        conn.execute("DELETE FROM providers WHERE id = ?", (pid,))
        conn.commit()
        conn.close()

    @staticmethod
    def update_models(pid: int, models: list[str]):
        conn = get_db()
        conn.execute("UPDATE providers SET models = ? WHERE id = ?", (json.dumps(models), pid))
        conn.commit()
        conn.close()

    @staticmethod
    def reset_daily_quotas():
        today = datetime.utcnow().strftime("%Y-%m-%d")
        conn = get_db()
        conn.execute(
            "UPDATE providers SET current_requests_today = 0, last_reset_date = ? "
            "WHERE last_reset_date != ? OR last_reset_date IS NULL",
            (today, today)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def increment_requests(pid: int):
        conn = get_db()
        conn.execute(
            "UPDATE providers SET current_requests_today = current_requests_today + 1 WHERE id = ?",
            (pid,)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def record_model_success(pid: int, model_name: str):
        """Reset consecutive_failures to 0 for a specific model."""
        conn = get_db()
        provider = ProviderDAO.get_by_id(pid)
        if not provider:
            conn.close()
            return
        
        sm = provider.get("selected_models", [])
        updated = False
        for i, m in enumerate(sm):
            # Normalize to dict if it's a string
            if isinstance(m, str):
                m = {"model": m, "rpd": 0, "rpm": 0}
                sm[i] = m
            
            if m.get("model") == model_name:
                if m.get("consecutive_failures", 0) != 0:
                    m["consecutive_failures"] = 0
                    updated = True
                break
        
        if updated:
            conn.execute("UPDATE providers SET selected_models = ? WHERE id = ?", (json.dumps(sm), pid))
            conn.commit()
        conn.close()

    @staticmethod
    def record_model_failure(pid: int, model_name: str):
        """Increment consecutive_failures for a specific model and record timestamp."""
        conn = get_db()
        provider = ProviderDAO.get_by_id(pid)
        if not provider:
            conn.close()
            return

        sm = provider.get("selected_models", [])
        updated = False
        for i, m in enumerate(sm):
            # Normalize to dict if it's a string
            if isinstance(m, str):
                m = {"model": m, "rpd": 0, "rpm": 0}
                sm[i] = m

            if m.get("model") == model_name:
                m["consecutive_failures"] = m.get("consecutive_failures", 0) + 1
                m["last_failure_time"] = datetime.utcnow().isoformat()
                updated = True
                break
        
        if updated:
            conn.execute("UPDATE providers SET selected_models = ? WHERE id = ?", (json.dumps(sm), pid))
            conn.commit()
        conn.close()

    @staticmethod
    def reset_health(pid: int):
        """Reset consecutive_failures for all models of a provider."""
        conn = get_db()
        provider = ProviderDAO.get_by_id(pid)
        if not provider:
            conn.close()
            return

        sm = provider.get("selected_models", [])
        for m in sm:
            m["consecutive_failures"] = 0
        
        conn.execute("UPDATE providers SET selected_models = ? WHERE id = ?", (json.dumps(sm), pid))
        conn.commit()
        conn.close()

    @staticmethod
    def _parse(row) -> dict:
        d = dict(row)
        d["models"] = json.loads(d.get("models") or "[]")
        d["selected_models"] = json.loads(d.get("selected_models") or "[]")
        return d


class GroupDAO:
    @staticmethod
    def get_all() -> list[dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM model_groups").fetchall()
        conn.close()
        return [GroupDAO._parse(r) for r in rows]

    @staticmethod
    def get_page(page: int = 1, page_size: int = 20, name: str = "") -> dict:
        conn = get_db()
        where_clauses = []
        params = []
        if name:
            where_clauses.append("(name LIKE ? OR alias LIKE ?)")
            params.extend([f"%{name}%", f"%{name}%"])
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        total = conn.execute(f"SELECT COUNT(*) as cnt FROM model_groups{where_sql}", params).fetchone()["cnt"]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM model_groups{where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        ).fetchall()
        conn.close()
        return {
            "items": [GroupDAO._parse(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    @staticmethod
    def get_by_alias(alias: str) -> dict | None:
        conn = get_db()
        row = conn.execute("SELECT * FROM model_groups WHERE alias = ?", (alias,)).fetchone()
        conn.close()
        return GroupDAO._parse(row) if row else None

    @staticmethod
    def create(data: dict):
        conn = get_db()
        conn.execute(
            "INSERT INTO model_groups (name, alias, target_models, strategy) VALUES (?,?,?,?)",
            (data["name"], data["alias"],
             json.dumps(data.get("target_models", [])),
             data.get("strategy", "weighted_random"))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update(gid: int, data: dict):
        conn = get_db()
        conn.execute(
            "UPDATE model_groups SET name=?, alias=?, target_models=?, strategy=? WHERE id=?",
            (data["name"], data["alias"],
             json.dumps(data.get("target_models", [])),
             data.get("strategy", "weighted_random"),
             gid)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def delete(gid: int):
        conn = get_db()
        conn.execute("DELETE FROM model_groups WHERE id = ?", (gid,))
        conn.commit()
        conn.close()

    @staticmethod
    def _parse(row) -> dict:
        d = dict(row)
        d["target_models"] = json.loads(d.get("target_models") or "[]")
        return d


class UsageLogDAO:
    @staticmethod
    def insert(provider_id: int, model: str, usage: dict | None = None,
               status_code: int = 200, error_message: str | None = None):
        conn = get_db()
        prompt = (usage or {}).get("prompt_tokens", 0)
        completion = (usage or {}).get("completion_tokens", 0)
        total = (usage or {}).get("total_tokens", 0)
        conn.execute(
            """INSERT INTO usage_logs (provider_id, model, prompt_tokens, completion_tokens, total_tokens, status_code, error_message)
               VALUES (?,?,?,?,?,?,?)""",
            (provider_id, model, prompt, completion, total, status_code, error_message)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_recent(limit: int = 100) -> list[dict]:
        conn = get_db()
        rows = conn.execute(
            """SELECT l.*, p.name as provider_name
               FROM usage_logs l LEFT JOIN providers p ON l.provider_id = p.id
               ORDER BY l.timestamp DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [UsageLogDAO._normalize(r) for r in rows]

    @staticmethod
    def get_page(page: int = 1, page_size: int = 20,
                 provider_name: str = "", model: str = "",
                 only_errors: bool = False) -> dict:
        conn = get_db()
        where_clauses = []
        params = []
        if provider_name:
            where_clauses.append("p.name LIKE ?")
            params.append(f"%{provider_name}%")
        if model:
            where_clauses.append("l.model LIKE ?")
            params.append(f"%{model}%")
        if only_errors:
            where_clauses.append("l.status_code != 200")
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM usage_logs l LEFT JOIN providers p ON l.provider_id = p.id{where_sql}",
            params
        ).fetchone()["cnt"]
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"""SELECT l.*, p.name as provider_name
               FROM usage_logs l LEFT JOIN providers p ON l.provider_id = p.id
               {where_sql}
               ORDER BY l.timestamp DESC LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        ).fetchall()
        conn.close()
        return {
            "items": [UsageLogDAO._normalize(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    @staticmethod
    def _normalize(r) -> dict:
        d = dict(r)
        d["prompt_tokens"] = d.get("prompt_tokens") or 0
        d["completion_tokens"] = d.get("completion_tokens") or 0
        d["total_tokens"] = d.get("total_tokens") or 0
        d["provider_name"] = d.get("provider_name") or "N/A"
        d["timestamp"] = d.get("timestamp") or ""
        d["status_code"] = d.get("status_code") or 200
        d["error_message"] = d.get("error_message") or ""
        return d

    @staticmethod
    def count_today(provider_id: int, model: str) -> int:
        conn = get_db()
        row = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM usage_logs
            WHERE provider_id = ?
              AND model = ?
              AND timestamp >= datetime('now'
                , 'start of day')
            """,
            (provider_id, model)
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def count_last_minute(provider_id: int) -> int:
        """Count requests for a provider in the last 60 seconds (DB-persisted RPM)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE provider_id = ? AND timestamp >= datetime('now', '-60 seconds')",
            (provider_id,)
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def count_last_minute_by_model(provider_id: int, model: str) -> int:
        """Count requests for a provider+model in the last 60 seconds (DB-persisted per-model RPM)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE provider_id = ? AND model = ? AND timestamp >= datetime('now', '-60 seconds')",
            (provider_id, model)
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def count_all(provider_id: int) -> int:
        """Total request count for a provider (all time)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE provider_id = ?",
            (provider_id,)
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def sum_tokens(provider_id: int) -> int:
        """Total tokens for a provider (all time)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) as total FROM usage_logs WHERE provider_id = ?",
            (provider_id,)
        ).fetchone()
        conn.close()
        return row["total"] if row else 0

    @staticmethod
    def count_all_by_model(provider_id: int, model: str) -> int:
        """Total request count for a provider+model (all time)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs WHERE provider_id = ? AND model = ?",
            (provider_id, model)
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def sum_tokens_by_model(provider_id: int, model: str) -> int:
        """Total tokens for a provider+model (all time)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) as total FROM usage_logs WHERE provider_id = ? AND model = ?",
            (provider_id, model)
        ).fetchone()
        conn.close()
        return row["total"] if row else 0

    @staticmethod
    def sum_tokens_last_minute_by_model(provider_id: int, model: str) -> int:
        """Sum tokens for a provider+model in the last 60 seconds (per-model TPM)."""
        conn = get_db()
        row = conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) as total FROM usage_logs WHERE provider_id = ? AND model = ? AND timestamp >= datetime('now', '-60 seconds')",
            (provider_id, model)
        ).fetchone()
        conn.close()
        return row["total"] if row else 0
