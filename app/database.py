"""Persistencia local y trazabilidad para TramIA."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class TramDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    citizen_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    description TEXT NOT NULL,
                    procedure_type TEXT,
                    status TEXT NOT NULL,
                    human_review INTEGER NOT NULL DEFAULT 0,
                    guide_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    valid INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(request_id) REFERENCES requests(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    agent TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(request_id) REFERENCES requests(id) ON DELETE CASCADE
                );
                """
            )

    def create_request(self, request: dict[str, Any], documents: list[dict[str, Any]]) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO requests
                (code, citizen_name, email, description, procedure_type, status, human_review, guide_json)
                VALUES (:code, :citizen_name, :email, :description, :procedure_type, :status,
                        :human_review, :guide_json)
                """,
                request,
            )
            request_id = int(cursor.lastrowid)
            connection.executemany(
                "INSERT INTO documents (request_id, name, valid) VALUES (?, ?, ?)",
                [(request_id, item["name"], int(bool(item.get("valid", False)))) for item in documents],
            )
            return request_id

    def add_audit(self, request_id: int, agent: str, action: str, detail: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO audit_log (request_id, agent, action, detail) VALUES (?, ?, ?, ?)",
                (request_id, agent, action, detail),
            )

    def update_status(self, request_id: int, status: str, human_review: bool | None = None) -> None:
        with self._connection() as connection:
            if human_review is None:
                connection.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
            else:
                connection.execute(
                    "UPDATE requests SET status = ?, human_review = ? WHERE id = ?",
                    (status, int(human_review), request_id),
                )

    def get_request(self, request_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["human_review"] = bool(result["human_review"])
            result["guide"] = json.loads(result.pop("guide_json"))
            result["documents"] = [
                {**dict(item), "valid": bool(item["valid"])}
                for item in connection.execute(
                    "SELECT id, name, valid FROM documents WHERE request_id = ? ORDER BY id", (request_id,)
                )
            ]
            result["traceability"] = [
                dict(item)
                for item in connection.execute(
                    """SELECT agent, action, detail, created_at FROM audit_log
                    WHERE request_id = ? ORDER BY id""",
                    (request_id,),
                )
            ]
            return result

    def pending_human_reviews(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id, code, citizen_name, email, description, procedure_type, status, created_at
                FROM requests WHERE human_review = 1 ORDER BY created_at"""
            ).fetchall()
            return [dict(row) for row in rows]
