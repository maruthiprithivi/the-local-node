"""Load and validate the synthetic join, move, leave workload.

Entities are humans and non humans. Humans join, move and leave. Agents, MCP servers and skills are
added, changed (scope or owner) and removed, and an agent loses everything when its human owner leaves.
An owner is stored as the fact owner:<id>, so an owner change is a revoke plus a write like any other."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .traps import TRAP_AXES

DEFAULT_WORKLOAD = Path(__file__).resolve().parent.parent / "workload" / "jml.yaml"
ENTITY_KINDS = ("human", "agent", "mcp_server", "skill")
EVENT_KINDS = {
    "human": ("join", "move", "leave"),
    "agent": ("add", "change", "remove", "owner_leaves"),
    "mcp_server": ("add", "change", "remove", "owner_leaves"),
    "skill": ("add", "change", "remove", "owner_leaves"),
}
ADDS, CHANGES, REMOVES = ("join", "add"), ("move", "change"), ("leave", "remove", "owner_leaves")


@dataclass
class Event:
    kind: str
    grant: list = field(default_factory=list)
    revoke: list = field(default_factory=list)
    revoke_all: bool = False
    department: str | None = None
    from_dept: str | None = None
    to_dept: str | None = None
    owner: str | None = None          # add: the owner; owner_leaves: the owner who left
    owner_from: str | None = None     # change: owner hand over
    owner_to: str | None = None
    expect_has: list = field(default_factory=list)
    expect_lacks: list = field(default_factory=list)
    answer: str | None = None


@dataclass
class Entity:
    id: str
    kind: str
    name: str
    events: list


@dataclass
class Trap:
    axis: str
    asker: str
    ask: str
    about: str
    asked_after: list
    expect: str
    confuse_with: str | None = None   # entity trap: the near namesake the answer must not leak
    probes: list = field(default_factory=list)  # asks at a point in the timeline, with ground truth


@dataclass
class Workload:
    name: str
    seed: int
    entities: list
    traps: list

    def entity(self, eid):
        for e in self.entities:
            if e.id == eid:
                return e
        raise KeyError(eid)

    person = entity

    @property
    def people(self):
        return [e for e in self.entities if e.kind == "human"]


def _event(ent, e):
    kinds = EVENT_KINDS[ent["kind"]]
    if e["kind"] not in kinds:
        raise ValueError(f"{ent['id']}: event {e['kind']!r} is not valid for a {ent['kind']}; use one of {', '.join(kinds)}")
    rv = e.get("revoke", [])
    grant, revoke = list(e.get("grant", [])), [] if rv == "all" else list(rv)
    own = e.get("owner"); ofrom = oto = owner = None
    if isinstance(own, dict):
        ofrom, oto = own["from"], own["to"]
        revoke.append(f"owner:{ofrom}"); grant.append(f"owner:{oto}")
    elif own is not None:
        owner = own
        if e["kind"] == "add":
            grant.insert(0, f"owner:{own}")
    exp = e.get("expect_after", {})
    return Event(kind=e["kind"], grant=grant, revoke=revoke, revoke_all=(rv == "all" or e["kind"] in REMOVES),
                 department=e.get("department"), from_dept=e.get("from"), to_dept=e.get("to"),
                 owner=owner, owner_from=ofrom, owner_to=oto,
                 expect_has=list(exp.get("has", [])), expect_lacks=list(exp.get("lacks", [])), answer=exp.get("answer"))


def load(path=DEFAULT_WORKLOAD):
    raw = yaml.safe_load(Path(path).read_text())
    ents = []
    for ent in raw["entities"]:
        if ent.get("kind") not in ENTITY_KINDS:
            raise ValueError(f"{ent['id']}: unknown entity kind {ent.get('kind')!r}; use one of {', '.join(ENTITY_KINDS)}")
        ents.append(Entity(id=ent["id"], kind=ent["kind"], name=ent["name"], events=[_event(ent, e) for e in ent["events"]]))
    ids = {e.id for e in ents}
    for ent in ents:
        for ev in ent.events:
            for o in (ev.owner, ev.owner_from, ev.owner_to):
                if o and o not in ids:
                    raise ValueError(f"{ent.id}: owner {o} is not in the workload")
    traps = []
    for t in raw.get("traps", []):
        if t["axis"] not in TRAP_AXES:
            raise ValueError(f"unknown trap axis {t['axis']!r}; use one of {', '.join(TRAP_AXES)}")
        traps.append(Trap(**t))
    return Workload(name=raw["workload"], seed=int(raw["seed"]), entities=ents, traps=traps)
