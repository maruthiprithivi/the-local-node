"""Offline checks for the crash durability scoring (no database)."""
import unittest

from ctxlayer import crash, workload


class CrashScore(unittest.TestCase):
    def setUp(self):
        self.ops = crash.jml_ops(workload.load())
        self.held, self.revoked = crash.expected_state(self.ops)
        self.state = {"jml_acked": len(self.ops), "held": {k: sorted(v) for k, v in self.held.items()},
                      "revoked": {k: sorted(v) for k, v in self.revoked.items()}, "tail_acked": ["tail:000000", "tail:000001"]}

    def test_ops_cover_people_and_non_humans(self):
        kinds = {s.person[0] for s in self.ops}
        self.assertTrue({"E", "A", "M", "S"} <= kinds)
        self.assertTrue({"write", "revoke", "forget"} <= {s.action for s in self.ops})

    def test_leaver_has_nothing_and_revoked_grants_recorded(self):
        self.assertEqual(self.held["E1001"], set())          # moved then left
        self.assertIn("ticket_queue", self.revoked["E1001"])  # moved away from support
        self.assertIn("ledger_read", self.revoked["E1001"])   # revoked on leave

    def test_full_recovery(self):
        got = {k: set(v) for k, v in self.held.items()}; got[crash.TAIL_ID] = {"tail:000000", "tail:000001", "tail:000002"}
        r = crash.score(self.state, got)
        self.assertEqual(r["records_lost"], 0); self.assertEqual(r["stale_resurfaced"], 0)
        self.assertEqual(r["records_recovered"], r["records_expected"]); self.assertEqual(r["unacked_tail_present"], 1)

    def test_total_loss(self):
        r = crash.score(self.state, {})
        self.assertEqual(r["records_recovered"], 0); self.assertEqual(r["records_lost"], r["records_expected"])

    def test_stale_resurfaces(self):
        got = {k: set(v) for k, v in self.held.items()}; got["E1001"] = {"ledger_read"}
        r = crash.score(self.state, got)
        self.assertEqual(r["stale_resurfaced"], 1); self.assertEqual(r["stale_list"], ["E1001:ledger_read"])

    def test_re_granted_fact_not_counted_stale(self):
        held, revoked = crash.expected_state([type("S", (), {"person": "X", "action": a, "facts": f})()
                                              for a, f in (("write", ["a"]), ("revoke", ["a"]), ("write", ["a"]))])
        self.assertEqual(held["X"], {"a"}); self.assertEqual(revoked["X"], set())


if __name__ == "__main__":
    unittest.main()
