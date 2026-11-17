"""Offline checks for the neo4j (Community server) adapter.

The graph operations are the same as relate; this file checks the
registry entry and that the shared Cypher still passes the workload
when the adapter is named neo4j.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ctxlayer import adapters, runner, workload
from ctxlayer.neo4j_adapter import Neo4j
from tests.test_relate import FakeDriver


class Neo4jAdapterOffline(unittest.TestCase):
    def test_registered_ready(self):
        b = adapters.get("neo4j")
        self.assertEqual(b.status, adapters.READY)
        self.assertEqual(b.group, "graph_knowledge")
        inst = b.make()
        self.assertIsInstance(inst, Neo4j)
        self.assertEqual(inst.name, "neo4j")

    def test_read_back_after_delete(self):
        d = FakeDriver(); a = Neo4j(driver=d); a.setup()
        a.write("E1", ["x", "y"]); self.assertEqual(a.read_back("E1"), {"x", "y"})
        a.revoke("E1", ["x"]); self.assertEqual(a.read_back("E1"), {"y"})
        a.forget("E1"); self.assertEqual(a.read_back("E1"), set())
        a.teardown(); self.assertTrue(d.closed)

    def test_full_workload_read_backs_pass(self):
        fake = FakeDriver()
        be = adapters.Backend("neo4j", "graph_knowledge", adapters.READY, lambda: Neo4j(driver=fake))
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                path = runner.run(workload.load(), be, out=d, run_id="neo4j-t1")
            recs = [json.loads(x) for x in Path(path).read_text().splitlines()]
        rb = [r for r in recs if r["action"] == "read_back"]
        self.assertTrue(all(r["pass"] for r in rb))
        self.assertEqual(len(rb), 23)
        self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()
