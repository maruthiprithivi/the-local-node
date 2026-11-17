"""pgvector baseline: a plain vector store with no access control of its own.

Facts are rows with a deterministic hashed embedding (no model, no network, seeded by the text).
write inserts, revoke and forget DELETE rows, read_back is a real SELECT. ask() does what a vector
store does: nearest rows by cosine distance to the question, filtered only by the entity named in the
question. It never looks at who asked, so identity_permission traps are expected to be the weak axis.
Connection comes from CTXLAYER_PG_DSN (never printed)."""
import hashlib
import os
from pathlib import Path

from .adapters import Adapter

DIM = 64
SCHEMA = Path(__file__).resolve().parent.parent / "backends" / "pgvector" / "schema.sql"


def embed(text):
    v = [0.0] * DIM
    for tok in text.lower().replace("_", " ").replace(":", " ").split():
        h = int.from_bytes(hashlib.sha256(tok.encode()).digest()[:4], "big")
        v[h % DIM] += 1.0 if (h >> 8) & 1 else -1.0
    n = sum(x * x for x in v) ** 0.5 or 1.0
    return "[" + ",".join(f"{x / n:.6f}" for x in v) + "]"


class PgVector(Adapter):
    name = "pgvector"

    def __init__(self, connect=None):
        self._connect = connect
        self.conn = None

    def setup(self):
        if self._connect is None:
            import psycopg
            dsn = os.environ.get("CTXLAYER_PG_DSN")
            if not dsn:
                raise SystemExit("set CTXLAYER_PG_DSN to a local pgvector database (see backends/pgvector/compose.yaml)")
            self._connect = lambda: psycopg.connect(dsn, autocommit=True)
        self.conn = self._connect()
        for stmt in SCHEMA.read_text().split(";"):
            if stmt.strip():
                self.conn.execute(stmt)

    def write(self, person_id, facts):
        for f in facts:
            self.conn.execute(
                "INSERT INTO memory (entity_id, fact, embedding) VALUES (%s, %s, %s::vector) ON CONFLICT DO NOTHING",
                (person_id, f, embed(f)))

    def revoke(self, person_id, facts):
        self.conn.execute("DELETE FROM memory WHERE entity_id = %s AND fact = ANY(%s)", (person_id, list(facts)))

    def forget(self, person_id):
        self.conn.execute("DELETE FROM memory WHERE entity_id = %s", (person_id,))

    def read_back(self, person_id):
        return {r[0] for r in self.conn.execute("SELECT fact FROM memory WHERE entity_id = %s", (person_id,)).fetchall()}

    def ask(self, asker_id, question, about_id):
        rows = self.conn.execute(
            "SELECT fact FROM memory WHERE entity_id = %s ORDER BY embedding <=> %s::vector LIMIT 5",
            (about_id, embed(question))).fetchall()
        return {r[0] for r in rows}

    def teardown(self):
        if self.conn:
            self.conn.close()
