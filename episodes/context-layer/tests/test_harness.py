import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from ctxlayer import adapters, cli, plan, workload
from ctxlayer.traps import TRAP_AXES


def out(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli.main(list(argv))
    return buf.getvalue()


class Harness(unittest.TestCase):
    def setUp(self):
        self.wl = workload.load()

    def test_four_trap_axes(self):
        self.assertEqual(TRAP_AXES, ("freshness", "identity_permission", "entity", "meaning_flip"))
        self.assertEqual({t.axis for t in self.wl.traps}, set(TRAP_AXES))

    def test_example_person_joins_support_moves_to_finance_then_leaves(self):
        p = self.wl.person("E1001")
        self.assertEqual([e.kind for e in p.events], ["join", "move", "leave"])
        self.assertEqual(p.events[0].department, "support")
        self.assertEqual((p.events[1].from_dept, p.events[1].to_dept), ("support", "finance"))
        self.assertEqual(p.events[2].expect_has, [])

    def test_entity_kinds_cover_non_human_lifecycle(self):
        self.assertEqual(workload.ENTITY_KINDS, ("human", "agent", "mcp_server", "skill"))
        kinds = {e.kind for e in self.wl.entities}
        self.assertEqual(kinds, set(workload.ENTITY_KINDS))
        for e in self.wl.entities:
            if e.kind != "human":
                evs = [x.kind for x in e.events]
                self.assertEqual(evs[0], "add"); self.assertIn("change", evs)
                self.assertIn(evs[-1], ("remove", "owner_leaves"))
                self.assertEqual(e.events[-1].expect_has, [])

    def test_agent_whose_owner_leaves_loses_access(self):
        a = self.wl.entity("A2002")
        self.assertEqual(a.events[-1].kind, "owner_leaves")
        self.assertEqual(self.wl.entity(a.events[-1].owner).events[-1].kind, "leave")

    def test_traps_cover_non_humans(self):
        nh = {e.id for e in self.wl.entities if e.kind != "human"}
        self.assertTrue({t.axis for t in self.wl.traps if t.about in nh or t.asker in nh} >= {"freshness", "identity_permission"})

    def test_every_axis_probes_every_non_human_kind(self):
        kinds = {e.id: e.kind for e in self.wl.entities}
        seen = {(t.axis, kinds[p["entity"]]) for t in self.wl.traps for p in t.probes}
        for axis in TRAP_AXES:
            for k in ("agent", "mcp_server", "skill"):
                self.assertIn((axis, k), seen, f"{axis} has no probe about a {k}")

    def test_owner_change_is_revoke_then_write_with_read_backs(self):
        steps = [s for s in plan.build(self.wl, adapters.get("no-memory"), "A2001")]
        acts = [s.action for s in steps if s.person == "A2001" and s.action != "trap"]
        self.assertEqual(acts, ["write", "read_back", "revoke", "read_back", "write", "read_back", "forget", "read_back"])

    def test_every_change_is_read_back(self):
        for name in adapters.REGISTRY:
            steps = plan.build(self.wl, adapters.get(name))
            self.assertTrue(plan.check_read_back_rule(steps), name)

    def test_stubs_are_not_implemented(self):
        for b in adapters.REGISTRY.values():
            if b.status != adapters.READY and b.factory is None:
                with self.assertRaises(NotImplementedError):
                    b.make().setup()

    def test_dry_run_prints_no_numbers_beyond_ordinals_and_ids(self):
        text = out("plan", "--backend", "pgvector", "--dry-run")
        self.assertIn("read back", text)
        scrub = re.sub(r"step \d+", "", text)
        scrub = re.sub(r"[EAMS]\d{4}", "", scrub)
        scrub = scrub.replace("mem0", "").replace("neo4j", "")
        self.assertIsNone(re.search(r"\d", scrub), scrub)

    def test_list_backends_has_no_digits_beyond_names(self):
        text = out("list-backends").replace("mem0", "").replace("neo4j", "")
        self.assertIsNone(re.search(r"\d", text))

    def test_no_memory_baseline_runs(self):
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                path = cli.cmd_run(type("A", (), {"workload": workload.DEFAULT_WORKLOAD, "backend": "no-memory",
                                                  "entity": None, "out": d})())
            recs = [json.loads(x) for x in next(Path(d).glob("no-memory-*.jsonl")).read_text().splitlines()]
        rb = [r for r in recs if r["action"] == "read_back"]
        self.assertTrue(rb)
        self.assertTrue(all(r["leaked"] == [] for r in rb))          # nothing stored, nothing leaks
        self.assertFalse(all(r["pass"] for r in rb))                 # and nothing is known



class PgVectorAdapterOffline(unittest.TestCase):
    """Offline check with an in-memory fake connection: write, revoke and forget really remove rows."""
    def test_read_back_after_delete(self):
        from ctxlayer.pgvector_adapter import PgVector, embed
        rows = set()

        class R:
            def __init__(s, r): s.r = r
            def fetchall(s): return s.r

        class C:
            def execute(s, q, a=()):
                if q.startswith("INSERT"): rows.add((a[0], a[1]))
                elif "fact = ANY" in q: rows.difference_update({(a[0], f) for f in a[1]})
                elif q.startswith("DELETE"): rows.difference_update({r for r in rows if r[0] == a[0]})
                elif q.startswith("SELECT"): return R([(f,) for e, f in rows if e == a[0]])
            def close(s): pass

        a = PgVector(connect=C); a.conn = C()
        a.write("E1", ["x", "y"]); self.assertEqual(a.read_back("E1"), {"x", "y"})
        a.revoke("E1", ["x"]); self.assertEqual(a.read_back("E1"), {"y"})
        a.forget("E1"); self.assertEqual(a.read_back("E1"), set())
        self.assertEqual(embed("a b"), embed("a b"))


class TrapScoring(unittest.TestCase):
    def test_probes_sit_after_their_event_and_every_axis_has_one(self):
        wl = workload.load(); steps = plan.build(wl, adapters.get("no-memory"))
        assert plan.check_read_back_rule(steps)
        axes = {s.trap.axis for s in steps if s.action == "trap"}
        self.assertEqual(axes, set(TRAP_AXES))
        for i, s in enumerate(steps):
            if s.action == "trap":   # a probe never sits before the read back of its event
                self.assertIn(steps[i - 1].action, ("read_back", "trap"))

    def test_score_probe(self):
        from ctxlayer.runner import score_probe
        self.assertTrue(score_probe({"empty": True}, [])["pass"])
        self.assertFalse(score_probe({"empty": True}, ["x"])["pass"])
        self.assertFalse(score_probe({"has": ["a"], "lacks": ["b"]}, ["b"])["pass"])
        self.assertTrue(score_probe({"has": ["a"], "lacks": ["b"]}, ["a"])["pass"])

    def test_no_memory_trap_scoring(self):
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                cli.main(["run", "--backend", "no-memory", "--out", d, "--run-id", "t1"])
            recs = [json.loads(x) for x in (Path(d) / "t1.jsonl").read_text().splitlines()]
        traps = [r for r in recs if r["action"] == "trap"]
        self.assertTrue(all(r["scored"] for r in traps))
        self.assertTrue(any(r["pass"] for r in traps))      # empty answers are right for the leaver traps
        self.assertFalse(all(r["pass"] for r in traps))


if __name__ == "__main__":
    unittest.main()
