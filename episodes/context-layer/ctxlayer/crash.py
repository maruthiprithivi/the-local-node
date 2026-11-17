"""Crash durability check: in-memory vs file mode.

write:  wipe the store, apply every JML change (people join/move/leave, agents, MCP servers, skills added,
        changed, removed) through the adapter, record each acknowledged change, then keep appending tail
        records (T9001 tail:NNNNNN) one per transaction, flushing each ack to disk, until the container is
        hard killed (docker kill -s KILL) by the driver script.
verify: after a restart on the same store, read every entity back (no setup, no wipe) and compare with the
        state the acknowledged changes imply: recovered, lost, and stale access that resurfaced
        (a fact that was revoked or forgotten before the kill and is back after the restart).
The adapter call returns only after Neo4j commits, so an ack means a committed transaction."""
import argparse
import json
import os
import sys
import time

from . import adapters, plan, workload

TAIL_ID = "T9001"


def jml_ops(wl):
    """The change steps (write, revoke, forget) of the full plan, in plan order."""
    return [s for s in plan.build(wl, adapters.get("relate")) if s.action in ("write", "revoke", "forget")]


def expected_state(ops):
    """Apply ops to a model. Returns (held: entity -> set, revoked: entity -> facts removed and not re-held)."""
    held, revoked = {}, {}
    for s in ops:
        h, r = held.setdefault(s.person, set()), revoked.setdefault(s.person, set())
        if s.action == "write":
            h |= set(s.facts); r -= set(s.facts)
        elif s.action == "revoke":
            r |= h & set(s.facts); h -= set(s.facts)
        elif s.action == "forget":
            r |= h; h.clear()
    return held, revoked


def score(state, got):
    """state: the write phase JSON; got: entity -> facts read back after the restart."""
    held = {k: set(v) for k, v in state["held"].items()}
    revoked = {k: set(v) for k, v in state["revoked"].items()}
    tail_acked = set(state["tail_acked"])
    exp = {(e, f) for e, fs in held.items() for f in fs} | {(TAIL_ID, f) for f in tail_acked}
    present = {(e, f) for e, fs in got.items() for f in fs}
    stale = sorted(f"{e}:{f}" for e, fs in revoked.items() for f in fs if (e, f) in present)
    extra_tail = sorted(f for e, f in present - exp if e == TAIL_ID)   # committed, ack lost in the kill
    return {
        "jml_changes_acked": state["jml_acked"], "tail_writes_acked": len(tail_acked),
        "records_expected": len(exp), "records_recovered": len(exp & present), "records_lost": len(exp - present),
        "jml_records_expected": len([x for x in exp if x[0] != TAIL_ID]),
        "jml_records_recovered": len([x for x in exp & present if x[0] != TAIL_ID]),
        "stale_resurfaced": len(stale), "stale_list": stale, "unacked_tail_present": len(extra_tail),
        "lost_sample": sorted(f"{e}:{f}" for e, f in exp - present)[:10],
    }


def _adapter():
    from .relate_adapter import Relate
    a = Relate(); a.driver = None
    return a


def cmd_write(args):
    wl, a = workload.load(), _adapter()
    a.setup()   # wipe + constraints, as in every run
    ops = jml_ops(wl)
    held, revoked = expected_state(ops)
    for s in ops:
        {"write": lambda: a.write(s.person, s.facts), "revoke": lambda: a.revoke(s.person, s.facts),
         "forget": lambda: a.forget(s.person)}[s.action]()
    state = {"seed": wl.seed, "jml_acked": len(ops), "entities": sorted({s.person for s in ops}),
             "held": {k: sorted(v) for k, v in held.items()}, "revoked": {k: sorted(v) for k, v in revoked.items()},
             "jml_done_epoch": time.time()}
    with open(args.state, "w") as f:
        json.dump(state, f)
    acks = open(args.state + ".tail", "w")
    print("JML_DONE", flush=True)
    for i in range(args.tail_max):
        fact = f"tail:{i:06d}"
        try:
            a.write(TAIL_ID, [fact])
        except Exception as e:   # the kill: connection gone mid write
            print(f"tail write {i} failed after kill: {type(e).__name__}", flush=True)
            break
        acks.write(f"{fact} {time.time():.6f}\n"); acks.flush(); os.fsync(acks.fileno())
    acks.close()


def load_state(path):
    state = json.load(open(path))
    tail = [l.split() for l in open(path + ".tail") if l.strip()] if os.path.exists(path + ".tail") else []
    state["tail_acked"] = [t[0] for t in tail]
    state["last_ack_epoch"] = float(tail[-1][1]) if tail else state["jml_done_epoch"]
    return state


def cmd_verify(args):
    state, a = load_state(args.state), _adapter()
    from neo4j import GraphDatabase
    a.driver = GraphDatabase.driver(os.environ["CTXLAYER_NEO4J_URI"],
                                    auth=(os.environ.get("CTXLAYER_NEO4J_USER", "neo4j"), os.environ["CTXLAYER_NEO4J_PASSWORD"]),
                                    notifications_min_severity="OFF")   # an empty store warns on every unknown label
    a.driver.verify_connectivity()
    got = {e: sorted(a.read_back(e)) for e in state["entities"] + [TAIL_ID]}
    a.teardown()
    res = {"mode": args.mode, "rep": args.rep, **score(state, {k: set(v) for k, v in got.items()}),
           "kill_epoch": args.kill_epoch, "last_ack_to_kill_s": round(args.kill_epoch - state["last_ack_epoch"], 3)
           if args.kill_epoch else None, "restart_ready_s": args.restart_s, "got": got}
    json.dump(res, open(args.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("got", "lost_sample", "stale_list")}))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ctxlayer.crash")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write"); w.add_argument("--state", required=True); w.add_argument("--tail-max", type=int, default=100000)
    w.set_defaults(fn=cmd_write)
    v = sub.add_parser("verify"); v.add_argument("--state", required=True); v.add_argument("--out", required=True)
    v.add_argument("--mode", required=True); v.add_argument("--rep", type=int, required=True)
    v.add_argument("--kill-epoch", type=float, default=None); v.add_argument("--restart-s", type=float, default=None)
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
