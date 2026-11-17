"""Build the run plan. A plan is a flat list of steps; every change is followed by a read back.

We never trust a delete because the backend said it worked. After every write, revoke or forget,
the plan reads memory back and checks what actually comes out."""
from dataclasses import dataclass, field

from .traps import DESCRIPTIONS, TrapAxis

MEASURES = (
    ("correctness", "right facts after each step"),
    ("stale_leak", "old roles and leavers that come back"),
    ("read_latency", "read time, with run count"),
    ("tokens_added", "tokens memory adds to a prompt"),
    ("setup_steps", "setup steps to first query"),
)


@dataclass
class Step:
    section: str
    action: str          # setup | write | revoke | forget | read_back | trap | teardown
    text: str
    person: str | None = None
    facts: list = field(default_factory=list)
    expect_has: list = field(default_factory=list)
    expect_lacks: list = field(default_factory=list)
    trap: object = None
    probe: dict | None = None


def _j(xs):
    return ", ".join(xs)


def _section(e):
    return f"{'person' if e.kind == 'human' else e.kind.replace('_', ' ')} {e.id} {e.name}"


def build(workload, backend, entity_filter=None):
    steps = [Step("setup", "setup", f"start backend {backend.name} from its pinned setup"),
             Step("setup", "setup", "load the synthetic workload, made up entities only")]
    probes_at = {}
    for t in workload.traps:
        for pr in t.probes:
            probes_at.setdefault((pr["entity"], pr["event"]), []).append((t, pr))
    for ent in workload.entities:
        if entity_filter not in (None, ent.id):
            continue
        sec, eid, held = _section(ent), ent.id, []
        def rb(text, has, lacks):
            steps.append(Step(sec, "read_back", f"read back {eid}, expect {text}", eid, expect_has=has, expect_lacks=lacks))
        for e in ent.events:
            if e.kind in ("join", "add"):
                what = f"join {e.department}" if e.kind == "join" else "add"
                steps.append(Step(sec, "write", f"{what}: write {_j(e.grant)}", eid, e.grant))
                held += e.grant
                rb(_j(e.expect_has), e.expect_has, e.expect_lacks)
            elif e.kind in ("move", "change"):
                what = f"move {e.from_dept} to {e.to_dept}" if e.kind == "move" else "change"
                if e.owner_from:
                    what = f"change owner {e.owner_from} to {e.owner_to}"
                if e.revoke:
                    steps.append(Step(sec, "revoke", f"{what}: revoke {_j(e.revoke)}", eid, e.revoke))
                    held = [x for x in held if x not in e.revoke]
                    gone = f"{e.from_dept} access gone" if e.kind == "move" else f"{_j(e.revoke)} gone"
                    rb(gone, list(held), e.revoke)
                if e.grant:
                    steps.append(Step(sec, "write", f"{e.kind}: write {_j(e.grant)}", eid, e.grant))
                    held += e.grant
                    rb(_j(e.expect_has), e.expect_has, e.expect_lacks)
            else:
                what = {"leave": "leave", "remove": "remove", "owner_leaves": f"owner {e.owner} left"}[e.kind]
                steps.append(Step(sec, "forget", f"{what}: revoke all access for {eid}", eid))
                held = []
                rb(e.answer or "no access", [], e.expect_lacks)
            for t, pr in probes_at.get((ent.id, e.kind), []):
                steps.append(Step("traps, each scored pass or fail on its own", "trap",
                                  f"{t.axis:<21}{t.about}  after {ent.id} {e.kind}: {DESCRIPTIONS[TrapAxis(t.axis)]}", t.about, trap=t, probe=pr))
    for t in workload.traps:   # with a filter, keep traps that ask about, come from, or could be confused with it
        if t.probes:
            continue
        if entity_filter and entity_filter not in (t.about, t.asker, t.confuse_with):
            continue
        steps.append(Step("traps, each scored pass or fail on its own", "trap",
                          f"{t.axis:<21}{t.about}  {DESCRIPTIONS[TrapAxis(t.axis)]}", t.about, trap=t))
    steps.append(Step("teardown", "teardown", f"stop backend {backend.name} and keep its raw outputs"))
    return steps


def check_read_back_rule(steps):
    """Every change step must be followed directly by a read back of the same person."""
    for i, s in enumerate(steps):
        if s.action in ("write", "revoke", "forget"):
            nxt = steps[i + 1] if i + 1 < len(steps) else None
            if not nxt or nxt.action != "read_back" or nxt.person != s.person:
                return False
    return True
