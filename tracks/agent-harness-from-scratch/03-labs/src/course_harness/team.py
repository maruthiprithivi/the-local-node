"""Offline team server boundary: authenticated principals, memory ACLs and fences.

The fake authenticator represents a trusted host login middleware. A real server
must verify credentials before invoking this boundary. There is no HTTP server,
credential issuance, distributed transaction, or production security claim here.
Python callers sharing this process are trusted: private attributes are not an
isolation boundary. User-claimed identity fields never enter request operations.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
import sqlite3


class TeamError(ValueError):
    """Authorization, conflict or reconciliation is required."""


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    permissions: frozenset[str]


@dataclass(frozen=True)
class TaskEnvelope:
    version: int
    kind: str
    correlation_id: str
    principal: str
    scope: str
    capabilities: frozenset[str]
    artifacts: tuple[str, ...]
    deadline: float
    remaining_budget: int
    idempotency_key: str
    sequence: int


class Authenticator:
    """A host-owned fixture maps opaque login tokens to verified identities.

    Constructing/copying an AuthContext does not authenticate it. Only exact
    minted contexts are accepted. Tokens and contexts are never persisted/logged.
    """

    def __init__(self, sessions: dict[str, tuple[str, frozenset[str]]]):
        self._sessions = dict(sessions)
        self._issued = {}

    def authenticate(self, token: str) -> AuthContext:
        if token not in self._sessions:
            raise TeamError("authentication required")
        user_id, permissions = self._sessions[token]
        context = AuthContext(user_id, frozenset(permissions))
        self._issued[id(context)] = (context, token)
        return context

    def verify(self, context: AuthContext) -> AuthContext:
        issued = self._issued.get(id(context))
        if not issued or issued[0] is not context or issued[1] not in self._sessions:
            raise TeamError("verified host authentication required")
        if self._sessions[issued[1]] != (context.user_id, context.permissions):
            raise TeamError("authentication permissions changed")
        return context

    def revoke(self, token: str):
        """Host authentication administration; invalidates previously minted contexts."""
        self._sessions.pop(token, None)


class TeamBoundary:
    VERSION = 1

    def __init__(self, path, authenticator: Authenticator, clock, *, memberships=(), projects=(),
                 known_secrets=(), global_budget=16, artifact_scopes=None):
        self.authenticator, self.clock = authenticator, clock
        self.known_secrets = tuple(s for s in known_secrets if s)
        self.artifact_scopes = dict(artifact_scopes or {})
        if type(global_budget) is not int or not 0 <= global_budget <= 1024:
            raise TeamError("invalid host global budget")
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS team_meta (version INTEGER);
            CREATE TABLE IF NOT EXISTS team_members (user_id TEXT, team_id TEXT,
                PRIMARY KEY(user_id, team_id));
            CREATE TABLE IF NOT EXISTS team_projects (project_id TEXT PRIMARY KEY, team_id TEXT);
            CREATE TABLE IF NOT EXISTS team_controls (key TEXT PRIMARY KEY, value INTEGER);
            CREATE TABLE IF NOT EXISTS team_messages (
                task_id INTEGER, sequence INTEGER, fingerprint TEXT,
                envelope TEXT, payload TEXT,
                PRIMARY KEY(task_id, sequence));
            CREATE TABLE IF NOT EXISTS team_peer_artifacts (team_id TEXT, name TEXT, value TEXT,
                PRIMARY KEY(team_id, name));
            CREATE TABLE IF NOT EXISTS team_memory (
                id INTEGER PRIMARY KEY, scope TEXT, scope_id TEXT, key TEXT,
                owner TEXT, value TEXT, source TEXT, created REAL, expires REAL,
                version INTEGER, root_id INTEGER, UNIQUE(scope, scope_id, key));
            CREATE TABLE IF NOT EXISTS team_memory_history (
                memory_id INTEGER, version INTEGER, value TEXT, source TEXT,
                actor TEXT, at REAL, PRIMARY KEY(memory_id, version));
            CREATE TABLE IF NOT EXISTS team_tasks (
                id INTEGER PRIMARY KEY, team_id TEXT, dedup_key TEXT, payload TEXT,
                digest TEXT, required TEXT, status TEXT, owner TEXT,
                fence INTEGER DEFAULT 0, lease_until REAL, effective TEXT, result TEXT,
                requester TEXT, correlation TEXT, sequence INTEGER DEFAULT 0,
                deadline REAL, budget INTEGER DEFAULT 8, attempts INTEGER DEFAULT 0,
                cancelled INTEGER DEFAULT 0,
                UNIQUE(team_id, dedup_key));
        """)
        version = self.db.execute("SELECT version FROM team_meta").fetchone()
        if version and version[0] != self.VERSION:
            self.db.close()
            raise TeamError("unsupported team state version")
        if not version:
            self.db.execute("INSERT INTO team_meta VALUES (?)", (self.VERSION,))
        self.db.execute("INSERT OR IGNORE INTO team_controls VALUES ('budget', ?)", (global_budget,))
        self.db.execute("INSERT OR IGNORE INTO team_controls VALUES ('memory_revision', 0)")
        if not version:
            for user_id, team_id in memberships:
                self.set_membership(user_id, team_id, True)
            for project_id, team_id in projects:
                self.db.execute("INSERT OR IGNORE INTO team_projects VALUES (?, ?)", (project_id, team_id))

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        if self.db.in_transaction:
            yield
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        else:
            self.db.execute("COMMIT")

    def set_membership(self, user_id: str, team_id: str, enabled: bool):
        """Host-only ACL administration, never a harness/model-dispatched tool."""
        if not all(isinstance(value, str) and 0 < len(value) <= 256 for value in (user_id, team_id)) or type(enabled) is not bool:
            raise TeamError("invalid membership")
        if enabled:
            self.db.execute("INSERT OR IGNORE INTO team_members VALUES (?, ?)", (user_id, team_id))
        else:
            self.db.execute("DELETE FROM team_members WHERE user_id=? AND team_id=?", (user_id, team_id))
        self.db.execute("UPDATE team_controls SET value=value+1 WHERE key='memory_revision'")

    def _authorize(self, context, permission, team_id=None):
        principal = self.authenticator.verify(context)
        if permission not in principal.permissions:
            raise TeamError("permission denied")
        if team_id is not None:
            if not isinstance(team_id, str) or not 0 < len(team_id) <= 256:
                raise TeamError("invalid explicit team scope")
            if not self.db.execute("SELECT 1 FROM team_members WHERE user_id=? AND team_id=?", (principal.user_id, team_id)).fetchone():
                raise TeamError("team membership required")
        return principal

    def _task(self, task_id):
        if type(task_id) is not int or task_id < 1:
            raise TeamError("invalid task identity")
        row = self.db.execute("SELECT * FROM team_tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise TeamError("unknown task")
        return row

    def _scope(self, context, permission, scope, team_id, task_id, project_id=None):
        principal = self._authorize(context, permission)
        for value in (team_id, project_id):
            if value is not None and (not isinstance(value, str) or not 0 < len(value) <= 256):
                raise TeamError("invalid memory scope identity")
        if scope == "user" and team_id is None and task_id is None and project_id is None:
            return principal.user_id
        if scope == "team" and team_id and task_id is None and project_id is None:
            self._authorize(context, permission, team_id)
            return team_id
        if scope == "project" and project_id and task_id is None:
            project = self.db.execute("SELECT team_id FROM team_projects WHERE project_id=?", (project_id,)).fetchone()
            if not project or (team_id is not None and team_id != project[0]):
                raise TeamError("unknown project/team scope")
            self._authorize(context, permission, project[0])
            return project_id
        if scope == "task" and task_id is not None and project_id is None:
            task = self._task(task_id)
            if team_id is not None and task["team_id"] != team_id:
                raise TeamError("task/team scope mismatch")
            self._authorize(context, permission, task["team_id"])
            return str(task_id)
        raise TeamError("invalid explicit memory scope")

    def put_memory(self, context, key: str, value: str, source: str, retention: float,
                   *, scope="user", team_id=None, task_id=None, project_id=None, expected_version=0,
                   consent=False, classification="public") -> dict:
        scope_id = self._scope(context, "memory:write", scope, team_id, task_id, project_id)
        if scope != "user" and consent is not True:
            raise TeamError("sharing memory requires explicit consent")
        if scope != "user":
            self._authorize(context, "memory:publish")
        if not all(isinstance(text, str) and text and len(text) <= 4096 for text in (key, value, source)):
            raise TeamError("invalid memory content/size")
        if classification != "public" or any(secret in text for secret in self.known_secrets for text in (key, value, source)):
            raise TeamError("secret memory rejected")
        if type(retention) not in (int, float) or not isfinite(retention) or not 0 < retention <= 86400 * 30:
            raise TeamError("retention must be bounded by thirty days")
        if type(expected_version) is not int or expected_version < 0:
            raise TeamError("invalid expected version")
        with self.transaction():
            old = self.db.execute("SELECT * FROM team_memory WHERE scope=? AND scope_id=? AND key=?",
                                  (scope, scope_id, key)).fetchone()
            if (old["version"] if old else 0) != expected_version:
                raise TeamError("memory version conflict; inspect and reconcile")
            if old and old["expires"] <= self.clock():
                raise TeamError("expired memory must be deleted before replacement")
            if old:
                root = self.db.execute("SELECT expires FROM team_memory WHERE id=?", (old["root_id"],)).fetchone()
                if not root or root[0] <= self.clock():
                    raise TeamError("origin memory expired or revoked")
            version = expected_version + 1
            now = self.clock()
            if old:
                expires = now + retention
                if old["owner"] != context.user_id:
                    expires = min(expires, old["expires"])
                self.db.execute("UPDATE team_memory SET value=?,source=?,expires=?,version=? WHERE id=?",
                                (value, source, expires, version, old["id"]))
                memory_id = old["id"]
            else:
                memory_id = self.db.execute("""INSERT INTO team_memory
                    (scope,scope_id,key,owner,value,source,created,expires,version)
                    VALUES(?,?,?,?,?,?,?,?,?)""", (scope, scope_id, key, context.user_id, value,
                    source, now, now + retention, version)).lastrowid
                self.db.execute("UPDATE team_memory SET root_id=? WHERE id=?", (memory_id, memory_id))
            self.db.execute("INSERT INTO team_memory_history VALUES (?,?,?,?,?,?)",
                            (memory_id, version, value, source, context.user_id, now))
            self.db.execute("UPDATE team_controls SET value=value+1 WHERE key='memory_revision'")
        return {"id": memory_id, "version": version, "trust": "untrusted-team-memory"}

    def read_memory(self, context, *, scope="user", team_id=None, task_id=None, project_id=None) -> list[dict]:
        scope_id = self._scope(context, "memory:read", scope, team_id, task_id, project_id)
        # Publication never outlives its origin, including after an origin correction.
        rows = self.db.execute("""SELECT m.* FROM team_memory m JOIN team_memory root ON root.id=m.root_id
            WHERE m.scope=? AND m.scope_id=? AND m.expires>? AND root.expires>?
            ORDER BY m.id""", (scope, scope_id, self.clock(), self.clock())).fetchall()
        return [dict(row) | {"trust": "untrusted-team-memory", "access_policy": "owner-only" if scope == "user" else "current-team-member"} for row in rows]

    def memory_revision(self, context, **scope) -> int:
        """Authorize BEFORE validating any client cache. Never cache authorization.

        Clients must also honor row expiry; a revision counter alone is not a TTL.
        Previously disclosed copies cannot be erased by this service.
        """
        self._scope(context, "memory:read", scope.get("scope", "user"), scope.get("team_id"),
                    scope.get("task_id"), scope.get("project_id"))
        return self.db.execute("SELECT value FROM team_controls WHERE key='memory_revision'").fetchone()[0]

    def search_memory(self, context, query: str, **scope) -> list[dict]:
        if not isinstance(query, str) or len(query) > 256:
            raise TeamError("invalid search")
        return [row for row in self.read_memory(context, **scope)
                if query.casefold() in (row["key"] + " " + row["value"]).casefold()]

    def inspect_memory(self, context, memory_id: int) -> dict:
        row = self.db.execute("SELECT * FROM team_memory WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise TeamError("unknown memory")
        team = row["scope_id"] if row["scope"] == "team" else None
        task = int(row["scope_id"]) if row["scope"] == "task" else None
        project = row["scope_id"] if row["scope"] == "project" else None
        scope_id = self._scope(context, "memory:read", row["scope"], team, task, project)
        if scope_id != row["scope_id"]:
            raise TeamError("private user memory")
        root = self.db.execute("SELECT expires FROM team_memory WHERE id=?", (row["root_id"],)).fetchone()
        if row["expires"] <= self.clock() or not root or root[0] <= self.clock():
            raise TeamError("expired/revoked memory unavailable")
        history = [dict(item) for item in self.db.execute(
            "SELECT * FROM team_memory_history WHERE memory_id=? ORDER BY version", (memory_id,))]
        return dict(row) | {"history": history, "stale": row["expires"] <= self.clock(),
                            "trust": "untrusted-team-memory"}

    def publish_memory(self, context, memory_id: int, team_id: str, *, consent=False, expected_version=0) -> dict:
        with self.transaction():
            self._authorize(context, "memory:publish", team_id)
            original = self.inspect_memory(context, memory_id)
            if original["scope"] != "user" or original["owner"] != context.user_id:
                raise TeamError("only live owned user memory may be published")
            existing = self.db.execute("SELECT owner FROM team_memory WHERE scope='team' AND scope_id=? AND key=?",
                                       (team_id, original["key"])).fetchone()
            if existing and existing[0] != context.user_id:
                raise TeamError("publication cannot replace another owner's shared record")
            published = self.put_memory(context, original["key"], original["value"], original["source"],
                                        original["expires"] - self.clock(), scope="team", team_id=team_id,
                                        consent=consent, expected_version=expected_version)
            self.db.execute("UPDATE team_memory SET root_id=? WHERE id=?", (original["id"], published["id"]))
            return published

    def delete_memory(self, context, memory_id: int):
        principal = self._authorize(context, "memory:delete")
        with self.transaction():
            row = self.db.execute("SELECT owner FROM team_memory WHERE id=?", (memory_id,)).fetchone()
            if not row or row["owner"] != principal.user_id:
                raise TeamError("only owner can delete/revoke memory")
            ids = [r[0] for r in self.db.execute("SELECT id FROM team_memory WHERE id=? OR root_id=?", (memory_id, memory_id))]
            for deleted_id in ids:
                self.db.execute("DELETE FROM team_memory_history WHERE memory_id=?", (deleted_id,))
                self.db.execute("DELETE FROM team_memory WHERE id=?", (deleted_id,))
            self.db.execute("UPDATE team_controls SET value=value+1 WHERE key='memory_revision'")

    def revoke_publication(self, context, memory_id: int):
        """Remove the shared copy and history; keep the owner's private original."""
        self._authorize(context, "memory:delete")
        row = self.db.execute("SELECT scope,owner FROM team_memory WHERE id=?", (memory_id,)).fetchone()
        if not row or row["owner"] != context.user_id or row["scope"] == "user":
            raise TeamError("revocation requires a shared copy")
        self.delete_memory(context, memory_id)

    def prune_memory(self):
        """Host retention job erases expired rows and their published descendants."""
        with self.transaction():
            expired = [r[0] for r in self.db.execute("SELECT id FROM team_memory WHERE expires<=?", (self.clock(),))]
            for memory_id in expired:
                ids = [r[0] for r in self.db.execute("SELECT id FROM team_memory WHERE id=? OR root_id=?", (memory_id, memory_id))]
                for deleted_id in ids:
                    self.db.execute("DELETE FROM team_memory_history WHERE memory_id=?", (deleted_id,))
                    self.db.execute("DELETE FROM team_memory WHERE id=?", (deleted_id,))
            if expired:
                self.db.execute("UPDATE team_controls SET value=value+1 WHERE key='memory_revision'")

    def submit_task(self, context, team_id: str, dedup_key: str, payload: dict, required_permissions) -> int:
        if not isinstance(team_id, str) or not 0 < len(team_id) <= 256:
            raise TeamError("shared task requires explicit team scope")
        self._authorize(context, "task:submit", team_id)
        if not isinstance(payload, dict) or not isinstance(dedup_key, str) or not 0 < len(dedup_key) <= 256:
            raise TeamError("invalid shared task identity/payload")
        required = frozenset(required_permissions)
        if not required or not required <= context.permissions:
            raise TeamError("task cannot amplify submitter authority")
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        if len(encoded) > 8192:
            raise TeamError("shared task payload limit")
        identity = sha256((encoded + json.dumps(sorted(required))).encode()).hexdigest()
        with self.transaction():
            old = self.db.execute("SELECT id,digest FROM team_tasks WHERE team_id=? AND dedup_key=?", (team_id, dedup_key)).fetchone()
            if old:
                if old["digest"] != identity:
                    raise TeamError("duplicate identity has conflicting payload/permissions")
                return old["id"]
            if self.db.execute("SELECT COUNT(*) FROM team_tasks WHERE status IN ('queued','running','uncertain')").fetchone()[0] >= 32:
                raise TeamError("global queue capacity")
            return self.db.execute("""INSERT INTO team_tasks(team_id,dedup_key,payload,digest,required,status,requester,deadline)
                VALUES(?,?,?,?,?,'queued',?,?)""", (team_id, dedup_key, encoded, identity,
                    json.dumps(sorted(required)), context.user_id, self.clock() + 300)).lastrowid

    def inspect_task(self, context, task_id: int) -> dict:
        task = self._task(task_id)
        self._authorize(context, "task:work", task["team_id"])
        return dict(task) | {"trust": "untrusted-shared-task"}

    def claim_task(self, context, task_id: int, *, worker_permissions, lease_seconds=30) -> dict:
        if type(lease_seconds) not in (int, float) or not isfinite(lease_seconds) or not 0 < lease_seconds <= 300:
            raise TeamError("lease must be bounded")
        with self.transaction():
            task = self._task(task_id)
            principal = self._authorize(context, "task:work", task["team_id"])
            required = frozenset(json.loads(task["required"]))
            effective = principal.permissions & frozenset(worker_permissions) & required
            if effective != required:
                raise TeamError("worker lacks required intersected permissions")
            if task["status"] != "queued":
                raise TeamError("task not claimable; inspect or reconcile")
            if task["cancelled"] or task["budget"] <= 0 or task["deadline"] <= self.clock() or task["attempts"] >= 3:
                raise TeamError("task cancelled or bound exhausted")
            budget = self.db.execute("SELECT value FROM team_controls WHERE key='budget'").fetchone()[0]
            if budget <= 0:
                raise TeamError("global budget exhausted")
            self.db.execute("UPDATE team_controls SET value=value-1 WHERE key='budget'")
            fence = task["fence"] + 1
            self.db.execute("""UPDATE team_tasks SET status='running',owner=?,fence=?,lease_until=?,effective=?,
                budget=budget-1,attempts=attempts+1 WHERE id=?""",
                            (principal.user_id, fence, min(self.clock() + lease_seconds, task["deadline"]), json.dumps(sorted(effective)), task_id))
            return {"task_id": task_id, "fence": fence, "permissions": sorted(effective), "owner": principal.user_id}

    def _lease(self, context, task_id, fence):
        task = self._task(task_id)
        principal = self._authorize(context, "task:work", task["team_id"])
        if (type(fence) is not int or task["status"] != "running" or task["owner"] != principal.user_id
                or task["fence"] != fence or task["lease_until"] <= self.clock()
                or not frozenset(json.loads(task["effective"])) <= principal.permissions):
            raise TeamError("stale or unauthorized task lease")
        return task

    def complete_task(self, context, task_id: int, fence: int, result: dict):
        if not isinstance(result, dict):
            raise TeamError("shared task result must be an object")
        encoded = json.dumps(result, allow_nan=False)
        if len(encoded) > 8192:
            raise TeamError("shared task result limit")
        with self.transaction():
            self._lease(context, task_id, fence)
            self.db.execute("UPDATE team_tasks SET status='completed',result=?,owner=NULL,lease_until=NULL WHERE id=?",
                            (encoded, task_id))

    def execute_peer(self, context, task_id: int, fence: int, *, provider_name: str,
                     domain="coding", operation="read_file", approval_context=None) -> dict:
        """Run one actual offline harness under rechecked local policy and lease.

        The caller supplies a trusted, minted reviewer context for an exact
        synthetic artifact action. Provider metadata never grants approval.
        Each fixture tool consumes shared task/global budget before its effect.
        """
        from .core import Engine, Limits
        from .providers import FakeProvider, Reply, ToolCall
        from .tools import Policy, Registry, Tool, object_schema
        task = self._lease(context, task_id, fence)
        if task["budget"] <= 0 or self.db.execute("SELECT value FROM team_controls WHERE key='budget'").fetchone()[0] <= 0:
            raise TeamError("peer action budget exhausted before model work")
        if domain not in {"coding", "sre", "automation"} or not isinstance(provider_name, str) or not provider_name:
            raise TeamError("invalid configured fixture peer")
        policy = Policy(mode="semi", allowed=frozenset(json.loads(task["effective"])),
                        run_id=f"shared-{task_id}-{fence}", clock=self.clock)

        def effect(args, *, write=False):
            with self.transaction():
                current = self._lease(context, task_id, fence)
                capability = "record_artifact" if write else "read_file"
                if capability not in json.loads(current["effective"]):
                    raise TeamError("local action not authorized")
                global_left = self.db.execute("SELECT value FROM team_controls WHERE key='budget'").fetchone()[0]
                if current["budget"] <= 0 or global_left <= 0:
                    raise TeamError("shared action budget exhausted")
                self.db.execute("UPDATE team_tasks SET budget=budget-1 WHERE id=?", (task_id,))
                self.db.execute("UPDATE team_controls SET value=value-1 WHERE key='budget'")
                if write:
                    name = "follow-up-" + str(task_id)
                    self.db.execute("INSERT OR REPLACE INTO team_peer_artifacts VALUES (?,?,?)",
                                    (task["team_id"], name, "approved synthetic follow-up"))
                    return {"artifact": name, "scope": task["team_id"], "approved": True}
                return {"source": "synthetic-health" if domain == "sre" else "toy-code",
                        "scope": task["team_id"], "healthy": False, "trust": "untrusted-fixture"}

        registry = Registry([
            Tool("read_file", "Read one synthetic peer observation", object_schema(), lambda args: effect(args)),
            Tool("record_artifact", "Record exactly one scoped follow-up", object_schema(),
                 lambda args: effect(args, write=True), "write", task["team_id"]),
        ])
        if approval_context is not None:
            self._authorize(approval_context, "task:approve", task["team_id"])
            policy.approve(registry.tools["record_artifact"], {}, ttl=min(30, task["lease_until"] - self.clock()))
        provider = FakeProvider([
            Reply(calls=(ToolCall("peer-call-1", operation, {}),), metadata={"fixture_provider": provider_name}),
            Reply(text="scoped peer result", metadata={"fixture_provider": provider_name}),
        ])
        result = Engine(provider, registry, policy, limits=Limits(steps=2, calls=1), clock=self.clock).run(
            "Observe scoped fixture evidence" if operation == "read_file" else "Record an approved scoped follow-up")
        tool_errors = any("error" in json.loads(message["content"]) for message in result.messages if message["role"] == "tool")
        return {"stop_reason": "tool_error" if tool_errors else result.stop_reason, "trace": result.trace,
                "provider": provider_name, "domain": domain, "scope": task["team_id"],
                "messages": result.messages, "usage": result.usage or None,
                "remaining_budget": self._task(task_id)["budget"]}

    def recover_tasks(self) -> list[int]:
        """Host recovery fences expired workers; possible effects become uncertain."""
        with self.transaction():
            expired = [row[0] for row in self.db.execute(
                "SELECT id FROM team_tasks WHERE status='running' AND lease_until<=?", (self.clock(),))]
            for task_id in expired:
                self.db.execute("""UPDATE team_tasks SET status='uncertain',owner=NULL,
                    lease_until=NULL,fence=fence+1 WHERE id=?""", (task_id,))
            self.db.execute("""UPDATE team_tasks SET status='dead_letter'
                WHERE status='queued' AND (deadline<=? OR budget<=0 OR attempts>=3)""", (self.clock(),))
            return expired

    def reconcile_task(self, context, task_id: int, *, observed: bool, effect_completed: bool, result=None):
        """Only trusted observations permit completion or an explicit safe requeue.

        Fence tokens protect journal writes; an external executor would also need
        to enforce fences. They cannot undo an already performed external effect.
        """
        with self.transaction():
            task = self._task(task_id)
            self._authorize(context, "task:work", task["team_id"])
            if observed is not True or type(effect_completed) is not bool or task["status"] != "uncertain":
                raise TeamError("uncertain task requires explicit observation")
            encoded = json.dumps(result, allow_nan=False)
            if len(encoded) > 8192:
                raise TeamError("reconciliation result limit")
            self.db.execute("UPDATE team_tasks SET status=?,result=? WHERE id=?",
                            ("completed" if effect_completed else "dead_letter" if task["cancelled"] or task["budget"] <= 0
                             or task["attempts"] >= 3 or task["deadline"] <= self.clock() else "queued", encoded, task_id))

    def cancel_task(self, context, task_id: int):
        with self.transaction():
            task = self._task(task_id)
            self._authorize(context, "task:cancel", task["team_id"])
            if task["status"] == "completed":
                return
            status = "uncertain" if task["status"] in {"running", "uncertain"} else "cancelled"
            self.db.execute("""UPDATE team_tasks SET cancelled=1,status=?,fence=fence+1,
                owner=NULL,lease_until=NULL WHERE id=?""", (status, task_id))

    def _envelope(self, context, envelope):
        if not isinstance(envelope, TaskEnvelope):
            raise TeamError("versioned envelope required")
        if not isinstance(envelope.scope, str) or not 0 < len(envelope.scope) <= 256:
            raise TeamError("envelope requires explicit bounded scope")
        self._authorize(context, "task:work", envelope.scope)
        if (type(envelope.version) is not int or envelope.version != 1
                or envelope.kind not in {"task", "result", "handover"}
                or envelope.principal != context.user_id
                or type(envelope.sequence) is not int or envelope.sequence < 0
                or type(envelope.remaining_budget) is not int or not 0 <= envelope.remaining_budget <= 16
                or type(envelope.deadline) not in (int, float) or not isfinite(envelope.deadline)
                or not self.clock() < envelope.deadline <= self.clock() + 3600
                or not all(isinstance(s, str) and 0 < len(s) <= 256 for s in (envelope.correlation_id, envelope.idempotency_key))
                or not isinstance(envelope.capabilities, frozenset) or not envelope.capabilities <= context.permissions
                or len(envelope.artifacts) > 8
                or any(self.artifact_scopes.get(ref) != envelope.scope for ref in envelope.artifacts)):
            raise TeamError("invalid or unauthorized collaboration envelope")

    @staticmethod
    def _fingerprint(envelope, payload):
        identity = dict(vars(envelope)) | {"capabilities": sorted(envelope.capabilities), "payload": payload}
        return sha256(json.dumps(identity, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def _message(self, task_id, envelope, payload, fingerprint):
        encoded = dict(vars(envelope)) | {"capabilities": sorted(envelope.capabilities)}
        self.db.execute("INSERT INTO team_messages VALUES (?,?,?,?,?)", (task_id, envelope.sequence,
                        fingerprint, json.dumps(encoded, sort_keys=True), json.dumps(payload, allow_nan=False)))

    def messages(self, context, task_id: int) -> list[dict]:
        task = self._task(task_id)
        self._authorize(context, "task:work", task["team_id"])
        return [{"sequence": row["sequence"], "envelope": json.loads(row["envelope"]),
                 "payload": json.loads(row["payload"]), "trust": "untrusted-peer-message"}
                for row in self.db.execute("SELECT * FROM team_messages WHERE task_id=? ORDER BY sequence", (task_id,))]

    def receive_task(self, context, envelope: TaskEnvelope, payload: dict) -> int:
        self._envelope(context, envelope)
        if envelope.kind != "task" or envelope.sequence != 0 or envelope.remaining_budget < 1:
            raise TeamError("task envelope must start causal sequence zero with budget")
        with self.transaction():
            existing = self.db.execute("SELECT id FROM team_tasks WHERE team_id=? AND dedup_key=?",
                                       (envelope.scope, envelope.idempotency_key)).fetchone()
            fingerprint = self._fingerprint(envelope, payload)
            if existing:
                recorded = self.db.execute("SELECT fingerprint FROM team_messages WHERE task_id=? AND sequence=0", (existing[0],)).fetchone()
                if not recorded or recorded[0] != fingerprint:
                    raise TeamError("conflicting envelope redelivery")
                return existing[0]
            if self.db.execute("SELECT COUNT(*) FROM team_tasks WHERE correlation=?", (envelope.correlation_id,)).fetchone()[0] >= 2:
                raise TeamError("bounded collaboration fan-out")
            task_id = self.submit_task(context, envelope.scope, envelope.idempotency_key, payload, envelope.capabilities)
            self.db.execute("UPDATE team_tasks SET correlation=?,deadline=?,budget=? WHERE id=?",
                            (envelope.correlation_id, envelope.deadline, envelope.remaining_budget, task_id))
            self._message(task_id, envelope, payload, fingerprint)
            return task_id

    def receive_result(self, context, task_id: int, fence: int, envelope: TaskEnvelope, result: dict):
        """An exact recorded duplicate is receipt replay, never a new owner write."""
        self._envelope(context, envelope)
        if envelope.kind not in {"result", "handover"}:
            raise TeamError("expected result or handover")
        if not isinstance(result, dict) or len(json.dumps(result, allow_nan=False)) > 8192:
            raise TeamError("peer result must be a bounded object")
        with self.transaction():
            task = self._task(task_id)
            if task["team_id"] != envelope.scope or task["correlation"] != envelope.correlation_id or task["dedup_key"] != envelope.idempotency_key:
                raise TeamError("correlation/scope/idempotency mismatch")
            fingerprint = self._fingerprint(envelope, result)
            duplicate = self.db.execute("SELECT fingerprint FROM team_messages WHERE task_id=? AND sequence=?", (task_id, envelope.sequence)).fetchone()
            if duplicate:
                if duplicate[0] != fingerprint:
                    raise TeamError("conflicting result redelivery")
                return {"duplicate": True, "task_id": task_id}
            self._lease(context, task_id, fence)
            if (envelope.sequence != task["sequence"] + 1
                    or not envelope.capabilities <= frozenset(json.loads(task["required"]))
                    or envelope.remaining_budget > task["budget"] or envelope.deadline > task["deadline"]):
                raise TeamError("causal order or delegation authority/budget expansion")
            if envelope.kind == "result":
                self.complete_task(context, task_id, fence, result)
            else:
                self.db.execute("""UPDATE team_tasks SET status='queued',owner=NULL,lease_until=NULL,
                    fence=fence+1,required=?,budget=?,deadline=? WHERE id=?""",
                    (json.dumps(sorted(envelope.capabilities)), envelope.remaining_budget, envelope.deadline, task_id))
            self.db.execute("UPDATE team_tasks SET sequence=? WHERE id=?", (envelope.sequence, task_id))
            self._message(task_id, envelope, result, fingerprint)
            return {"duplicate": False, "task_id": task_id}


def checkpoint(lesson: int, scenario: str) -> dict:
    """Two authenticated fixture users on one SQLite server, never multi-host I/O."""
    if lesson not in {31, 32} or scenario not in {"coding", "sre", "automation"}:
        raise TeamError("unknown team checkpoint")
    permissions = frozenset({"memory:read", "memory:write", "memory:delete", "memory:publish",
                             "task:submit", "task:work", "task:cancel", "task:approve", "read_file", "record_artifact"})
    authenticator = Authenticator({"fixture-a": ("alice", permissions), "fixture-b": ("bob", permissions)})
    alice, bob = authenticator.authenticate("fixture-a"), authenticator.authenticate("fixture-b")
    clock, checks, trace = [100.0], {}, []
    server = TeamBoundary(":memory:", authenticator, lambda: clock[0], memberships=[("alice", "blue"), ("bob", "blue")],
                          projects=[("toy", "blue")], global_budget=8, artifact_scopes={"fixture/evidence": "blue"})

    def reject(label, operation):
        try:
            operation()
        except TeamError:
            checks[label] = True
            trace.append(label + ": rejected")
        else:
            checks[label] = False

    def envelope(principal, key, correlation, *, kind="task", sequence=0, budget=5, capabilities=frozenset({"read_file"})):
        return TaskEnvelope(1, kind, correlation, principal, "blue", capabilities,
                            ("fixture/evidence",), 200.0, budget, key, sequence)

    try:
        if lesson == 31:
            private = server.put_memory(alice, "preference", "private " + scenario, "alice fixture", 20)
            convention = server.put_memory(alice, "convention", "scoped fixture only", "project toy", 20)
            checks["private_before_publish"] = server.read_memory(bob) == []
            reject("forged_identity", lambda: server.read_memory(AuthContext("alice", permissions)))
            reject("publication_requires_consent", lambda: server.publish_memory(alice, convention["id"], "blue"))
            shared = server.publish_memory(alice, convention["id"], "blue", consent=True)
            checks["selected_shared_only"] = [r["key"] for r in server.read_memory(bob, scope="team", team_id="blue")] == ["convention"]
            corrected = server.put_memory(bob, "convention", "corrected fixture fact", "bob observation", 10,
                                         scope="team", team_id="blue", consent=True, expected_version=1)
            reject("optimistic_conflict", lambda: server.put_memory(alice, "convention", "stale correction", "alice", 10,
                    scope="team", team_id="blue", consent=True, expected_version=1))
            checks["attributed_history"] = server.inspect_memory(alice, corrected["id"])["history"][-1]["actor"] == "bob"
            server.put_memory(alice, "project", "toy project fact", "fixture", 10, scope="project", project_id="toy", consent=True)
            checks["project_acl"] = bool(server.read_memory(bob, scope="project", project_id="toy"))
            revision = server.memory_revision(bob, scope="team", team_id="blue")
            server.delete_memory(alice, convention["id"])
            checks["deleted_not_retrieved"] = server.search_memory(bob, "convention", scope="team", team_id="blue") == []
            checks["cache_invalidated"] = server.memory_revision(bob, scope="team", team_id="blue") > revision
            server.set_membership("bob", "blue", False)
            reject("revoked_before_retrieval", lambda: server.read_memory(bob, scope="team", team_id="blue"))
            reject("revoked_cache_authorization", lambda: server.memory_revision(bob, scope="team", team_id="blue"))
            checks["private_retained"] = any(r["id"] == private["id"] for r in server.read_memory(alice))
            trace.append("memory: alice shares selected fact; bob correction attributed; deleted and membership revoked")
        else:
            request = envelope("alice", "event-1", "correlation-1")
            task_id = server.receive_task(alice, request, {"scenario": scenario, "provider": "fake-coding"})
            checks["deduplicated"] = server.receive_task(alice, request, {"scenario": scenario, "provider": "fake-coding"}) == task_id
            first = server.claim_task(alice, task_id, worker_permissions={"read_file", "shell"})
            checks["permission_intersection"] = first["permissions"] == ["read_file"]
            coding = server.execute_peer(alice, task_id, first["fence"], provider_name="fake-coding", domain="coding")
            checks["coding_harness_ran"] = coding["stop_reason"] == "final"
            reject("out_of_order_result", lambda: server.receive_result(alice, task_id, first["fence"],
                   envelope("alice", "event-1", "correlation-1", kind="result", sequence=2, budget=3), {}))
            server.receive_result(alice, task_id, first["fence"], envelope("alice", "event-1", "correlation-1", kind="handover", sequence=1, budget=3),
                                  {"provider": "fake-sre", "uncertainty": "fixture observation only"})
            reject("stale_writer", lambda: server.complete_task(alice, task_id, first["fence"], {}))
            second = server.claim_task(bob, task_id, worker_permissions={"read_file"})
            sre = server.execute_peer(bob, task_id, second["fence"], provider_name="fake-sre", domain="sre")
            checks["sre_harness_ran"] = sre["stop_reason"] == "final" and sre["provider"] != coding["provider"]
            result = envelope("bob", "event-1", "correlation-1", kind="result", sequence=2, budget=1)
            server.receive_result(bob, task_id, second["fence"], result, {"evidence": "synthetic health"})
            checks["lost_ack_replay"] = server.receive_result(bob, task_id, second["fence"], result, {"evidence": "synthetic health"})["duplicate"]
            followup = server.receive_task(alice, envelope("alice", "follow-up", "correlation-1", budget=3,
                                           capabilities=frozenset({"record_artifact"})), {"evidence_task": task_id})
            automation_lease = server.claim_task(alice, followup, worker_permissions={"record_artifact"})
            pending = server.execute_peer(alice, followup, automation_lease["fence"], provider_name="fake-automation", domain="automation", operation="record_artifact")
            checks["followup_requires_approval"] = pending["stop_reason"] == "approval_required"
            automation = server.execute_peer(alice, followup, automation_lease["fence"], provider_name="fake-automation", domain="automation",
                                             operation="record_artifact", approval_context=alice)
            checks["automation_harness_ran"] = automation["stop_reason"] == "final"
            server.receive_result(alice, followup, automation_lease["fence"], envelope("alice", "follow-up", "correlation-1", kind="result", sequence=1,
                                  budget=1, capabilities=frozenset({"record_artifact"})), {"artifact": "approved follow-up"})
            cancelled = server.receive_task(alice, envelope("alice", "event-2", "correlation-2"), {})
            lease = server.claim_task(alice, cancelled, worker_permissions={"read_file"})
            server.cancel_task(alice, cancelled)
            reject("cancel_fences_worker", lambda: server.complete_task(alice, cancelled, lease["fence"], {}))
            checks["cancel_uncertain"] = server.inspect_task(alice, cancelled)["status"] == "uncertain"
            crashed = server.receive_task(alice, envelope("alice", "event-3", "correlation-3", budget=1), {})
            server.claim_task(bob, crashed, worker_permissions={"read_file"}, lease_seconds=5)
            clock[0] += 6
            checks["crash_uncertain"] = server.recover_tasks() == [crashed]
            reject("no_blind_retry", lambda: server.claim_task(bob, crashed, worker_permissions={"read_file"}))
            server.reconcile_task(bob, crashed, observed=True, effect_completed=False, result={"observation": "no effect"})
            checks["bounded_dead_letter"] = server.inspect_task(bob, crashed)["status"] == "dead_letter"
            queued = server.receive_task(alice, envelope("alice", "event-4", "correlation-4"), {})
            reject("global_budget", lambda: server.claim_task(alice, queued, worker_permissions={"read_file"}))
            trace.append("collaboration: scoped handover; fenced owners; result replay; cancel/crash uncertainty; budget exhausted")
        return {"lesson": lesson, "scenario": scenario, "status": "passed" if checks and all(checks.values()) else "failed",
                "stop_reason": "checkpoint_complete", "checks": checks, "trace": trace}
    finally:
        server.close()
