"""Small SQLite journal. Recording a result is different from repeating its effect.

The database is local to one educational resident service. It is not a distributed
transaction with a tool: a crash after an effect leaves explicit uncertainty.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class StateError(ValueError):
    """Invalid durable state or transition."""


class DurableStore:
    VERSION = 1

    def __init__(self, path: str | Path, *, clock: Callable[[], float] = time.time):
        self.clock = clock
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.row_factory = sqlite3.Row
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, self.VERSION):
            self.db.close()
            raise StateError(f"unsupported state version {version}")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, budgets TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, status TEXT NOT NULL,
                payload TEXT NOT NULL, scope TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, at REAL NOT NULL, kind TEXT NOT NULL,
                subject TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS controls (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY, dedup_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                ready_at REAL NOT NULL, owner TEXT, lease_until REAL, result TEXT,
                cancelled INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS schedules (name TEXT PRIMARY KEY, last_due REAL NOT NULL);
            PRAGMA user_version = 1;
        """)

    def close(self) -> None:
        self.db.close()

    def event(self, kind: str, subject: str, data: Any = None) -> None:
        self.db.execute("INSERT INTO events(at,kind,subject,data) VALUES(?,?,?,?)",
                        (self.clock(), kind, subject, json.dumps(data)))

    def events(self) -> list[dict]:
        return [dict(row) | {"data": json.loads(row["data"])}
                for row in self.db.execute("SELECT * FROM events ORDER BY id")]

    def create_run(self, run_id: str, budgets: dict[str, float]) -> None:
        if any(not math.isfinite(value) or value < 0 for value in budgets.values()):
            raise StateError("budgets must be nonnegative")
        with self.transaction():
            self.db.execute("INSERT INTO runs(id,budgets) VALUES(?,?)", (run_id, json.dumps(budgets)))
            self.event("run.created", run_id, budgets)

    def run(self, run_id: str) -> dict:
        row = self.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise StateError("unknown run")
        return dict(row) | {"budgets": json.loads(row["budgets"])}

    def consume(self, run_id: str, name: str, amount: float = 1) -> None:
        with self.transaction():
            run = self.run(run_id)
            if not math.isfinite(amount) or amount < 0 or run["cancelled"] or run["budgets"].get(name, 0) < amount:
                raise StateError("cancelled run or exhausted budget")
            run["budgets"][name] -= amount
            self.db.execute("UPDATE runs SET budgets=? WHERE id=?", (json.dumps(run["budgets"]), run_id))
            self.event("budget.consumed", run_id, {"name": name, "amount": amount})

    def cancel_run(self, run_id: str) -> None:
        with self.transaction():
            self.run(run_id)
            self.db.execute("UPDATE runs SET cancelled=1 WHERE id=?", (run_id,))
            self.event("run.cancelled", run_id)

    def request_action(self, run_id: str, action_id: str, payload: dict) -> None:
        with self.transaction():
            if self.run(run_id)["cancelled"]:
                raise StateError("cancelled run")
            self.db.execute("INSERT INTO actions(id,run_id,status,payload) VALUES(?,?,?,?)",
                            (action_id, run_id, "requested", json.dumps(payload)))
            self.event("action.requested", action_id, payload)

    def action(self, action_id: str) -> dict:
        row = self.db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        if row is None:
            raise StateError("unknown action")
        return dict(row) | {name: json.loads(row[name]) if row[name] is not None else None
                            for name in ("payload", "scope", "result")}

    def approve_action(self, action_id: str, scope: dict) -> None:
        """Persist a host-issued scope, not authority inferred from generated prose.

        Callers must bind scope to the exact request (tool, target, arguments,
        run identifier) with the policy request digest and enforce expiry before
        execution. This journal compares scopes; the policy owns permission.
        """
        with self.transaction():
            action = self.action(action_id)
            if action["status"] != "requested" or self.run(action["run_id"])["cancelled"]:
                raise StateError("action is not awaiting approval")
            self.db.execute("UPDATE actions SET status='approved',scope=? WHERE id=?",
                            (json.dumps(scope, sort_keys=True), action_id))
            self.event("action.approved", action_id, scope)

    def start_action(self, action_id: str, scope: dict) -> None:
        with self.transaction():
            action = self.action(action_id)
            if (action["status"] != "approved" or scope != action["scope"]
                    or self.run(action["run_id"])["cancelled"] or self.control("human_stop", False)):
                raise StateError("action lacks matching approval or execution is stopped")
            self.db.execute("UPDATE actions SET status='started' WHERE id=?", (action_id,))
            self.event("action.started", action_id)

    def complete_action(self, action_id: str, result: Any) -> None:
        with self.transaction():
            if self.action(action_id)["status"] != "started":
                raise StateError("only a started action can complete")
            self.db.execute("UPDATE actions SET status='completed',result=? WHERE id=?",
                            (json.dumps(result), action_id))
            self.event("action.completed", action_id, result)

    def recover(self) -> list[str]:
        """Call after exclusive startup, never while another worker is active."""
        with self.transaction():
            ids = [row[0] for row in self.db.execute("SELECT id FROM actions WHERE status='started'")]
            for action_id in ids:
                self.db.execute("UPDATE actions SET status='uncertain' WHERE id=?", (action_id,))
                self.event("action.uncertain", action_id)
            return ids

    def reconcile(self, action_id: str, result: Any, *, observed: bool) -> None:
        """An operator or authorized observation resolves uncertainty; never replay."""
        with self.transaction():
            if not observed or self.action(action_id)["status"] != "uncertain":
                raise StateError("reconciliation requires uncertain state and observation")
            self.db.execute("UPDATE actions SET status='completed',result=? WHERE id=?",
                            (json.dumps(result), action_id))
            self.event("action.reconciled", action_id, result)

    def control(self, key: str, default: Any = None) -> Any:
        row = self.db.execute("SELECT value FROM controls WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def set_control(self, key: str, value: Any) -> None:
        self.db.execute("INSERT INTO controls VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, json.dumps(value)))

    def transaction(self):
        """Explicit atomic writes; sqlite's autocommit context alone is insufficient."""
        from contextlib import contextmanager

        @contextmanager
        def atomic():
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            else:
                self.db.execute("COMMIT")
        return atomic()
