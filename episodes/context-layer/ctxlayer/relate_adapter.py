"""relate: the Neo4j DBMS that Neo4j Desktop (Relate) wraps, run as a pinned Neo4j Community container.

Graph model: (:Entity {id})-[:HAS]->(:Fact {entity_id, text}). write MERGEs fact nodes and edges,
revoke and forget DETACH DELETE them, read_back is a real MATCH. ask() does what a plain graph lookup
does: it follows HAS edges from the entity named in the question (capped at 5, like pgvector's top 5).
Like pgvector, it never looks at who asked: Neo4j Community has no per-user graph security
(role based access control is Enterprise only), so identity_permission is expected to be the weak axis.
Connection comes from CTXLAYER_NEO4J_URI / CTXLAYER_NEO4J_USER / CTXLAYER_NEO4J_PASSWORD (never printed)."""
import os
from pathlib import Path

from .adapters import Adapter

SCHEMA = Path(__file__).resolve().parent.parent / "backends" / "relate" / "schema.cypher"


def statements(text=None):
    text = SCHEMA.read_text() if text is None else text
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    return [s.strip() for s in body.split(";") if s.strip()]


class Relate(Adapter):
    name = "relate"

    def __init__(self, driver=None, database="neo4j"):
        self.driver = driver
        self.database = database

    def _q(self, cypher, **params):
        records, _, _ = self.driver.execute_query(cypher, params, database_=self.database)
        return records

    def setup(self):
        if self.driver is None:
            from neo4j import GraphDatabase
            uri = os.environ.get("CTXLAYER_NEO4J_URI")
            pw = os.environ.get("CTXLAYER_NEO4J_PASSWORD")
            if not uri or not pw:
                raise SystemExit("set CTXLAYER_NEO4J_URI and CTXLAYER_NEO4J_PASSWORD (see backends/relate/compose.yaml)")
            self.driver = GraphDatabase.driver(uri, auth=(os.environ.get("CTXLAYER_NEO4J_USER", "neo4j"), pw))
            self.driver.verify_connectivity()
        for stmt in statements():
            self._q(stmt)

    def write(self, person_id, facts):
        self._q("MERGE (e:Entity {id: $id}) WITH e UNWIND $facts AS t "
                "MERGE (f:Fact {entity_id: $id, text: t}) MERGE (e)-[:HAS]->(f)", id=person_id, facts=list(facts))

    def revoke(self, person_id, facts):
        self._q("MATCH (:Entity {id: $id})-[:HAS]->(f:Fact) WHERE f.text IN $facts DETACH DELETE f",
                id=person_id, facts=list(facts))

    def forget(self, person_id):
        self._q("MATCH (e:Entity {id: $id}) OPTIONAL MATCH (e)-[:HAS]->(f:Fact) DETACH DELETE f, e", id=person_id)

    def read_back(self, person_id):
        return {r["t"] for r in self._q("MATCH (:Entity {id: $id})-[:HAS]->(f:Fact) RETURN f.text AS t", id=person_id)}

    def ask(self, asker_id, question, about_id):
        rows = self._q("MATCH (:Entity {id: $about})-[:HAS]->(f:Fact) RETURN f.text AS t ORDER BY t LIMIT 5", about=about_id)
        return {r["t"] for r in rows}

    def teardown(self):
        if self.driver:
            self.driver.close()
