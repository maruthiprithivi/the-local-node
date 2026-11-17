"""Offline checks for the relate (Neo4j) adapter with an in-memory fake driver: write, revoke and
forget really remove facts, ask ignores the asker, and the full workload passes every read back."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ctxlayer import adapters, runner, workload
from ctxlayer.relate_adapter import Relate, statements


class FakeDriver:
    """Interprets exactly the Cypher the adapter sends, over a set of (entity, fact) edges."""
    def __init__(self):
        self.edges, self.entities, self.log, self.closed = set(), set(), [], False

    def execute_query(self, q, p=None, database_=None):
        p = p or {}; self.log.append(q)
        if q.startswith("MATCH (n) DETACH DELETE n"):
            self.edges.clear(); self.entities.clear(); rows = []
        elif q.startswith("CREATE CONSTRAINT"):
            rows = []
        elif q.startswith("MERGE (e:Entity"):
            self.entities.add(p["id"]); self.edges |= {(p["id"], t) for t in p["facts"]}; rows = []
        elif "WHERE f.text IN $facts DETACH DELETE" in q:
            self.edges -= {(p["id"], t) for t in p["facts"]}; rows = []
        elif "DETACH DELETE f, e" in q:
            self.entities.discard(p["id"]); self.edges = {e for e in self.edges if e[0] != p["id"]}; rows = []
        elif "RETURN f.text AS t ORDER BY t LIMIT 5" in q:
            rows = [{"t": t} for t in sorted(t for e, t in self.edges if e == p["about"])[:5]]
        elif "RETURN f.text AS t" in q:
            rows = [{"t": t} for e, t in self.edges if e == p["id"]]
        else:
            raise AssertionError(f"unexpected cypher: {q}")
        return rows, None, None

    def close(self): self.closed = True


class RelateAdapterOffline(unittest.TestCase):
    def test_registered_ready(self):
        b = adapters.get("relate")
        self.assertEqual(b.status, adapters.READY)
        self.assertEqual(b.group, "graph_knowledge")
        self.assertIsInstance(b.make(), Relate)
        # neo4j (Community server) is a separate registry entry, tested in test_neo4j.py
        self.assertEqual(adapters.get("neo4j").status, adapters.READY)

    def test_schema_statements(self):
        st = statements()
        self.assertEqual(st[0], "MATCH (n) DETACH DELETE n")
        self.assertTrue(all("IS UNIQUE" in s for s in st[1:]) and len(st) == 3)

    def test_read_back_after_delete(self):
        d = FakeDriver(); a = Relate(driver=d); a.setup()
        a.write("E1", ["x", "y"]); self.assertEqual(a.read_back("E1"), {"x", "y"})
        a.revoke("E1", ["x"]); self.assertEqual(a.read_back("E1"), {"y"})
        a.forget("E1"); self.assertEqual(a.read_back("E1"), set())
        a.teardown(); self.assertTrue(d.closed)

    def test_ask_ignores_asker(self):
        a = Relate(driver=FakeDriver()); a.setup(); a.write("E1", ["ledger_read"])
        self.assertEqual(a.ask("E9999", "What can E1 access?", "E1"), a.ask("E1", "What can E1 access?", "E1"))

    def test_full_workload_read_backs_pass(self):
        fake = FakeDriver()
        be = adapters.Backend("relate", "graph_knowledge", adapters.READY, lambda: Relate(driver=fake))
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                path = runner.run(workload.load(), be, out=d, run_id="relate-t1")
            recs = [json.loads(x) for x in Path(path).read_text().splitlines()]
        rb = [r for r in recs if r["action"] == "read_back"]
        kinds = {e.id: e.kind for e in workload.load().entities}
        self.assertEqual({kinds[r["person"]] for r in rb}, {"human", "agent", "mcp_server", "skill"})
        self.assertTrue(all(r["pass"] for r in rb))
        traps = [r for r in recs if r["action"] == "trap"]
        self.assertEqual({r["axis"] for r in traps}, {"freshness", "identity_permission", "entity", "meaning_flip"})
        self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()
