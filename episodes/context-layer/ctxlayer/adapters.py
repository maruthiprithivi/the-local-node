"""Backend adapter registry.

Every backend in the series implements the same small interface, so the workload, the read back
checks and the traps are identical for all of them. `no-memory`, `pgvector`, `relate` and `neo4j` are runnable.
Every other entry is a stub that is NOT IMPLEMENTED yet."""
from dataclasses import dataclass

READY, NEXT, PLANNED, HOSTED = "ready", "next", "planned", "hosted"
STATUS_TEXT = {
    READY: "ready",
    NEXT: "next, adapter in progress",
    PLANNED: "planned, not implemented",
    HOSTED: "hosted app, tested by hand",
}


class Adapter:
    """write and revoke change memory; read_back returns what the backend actually returns now."""
    name = "base"

    def setup(self): ...
    def write(self, person_id, facts): raise NotImplementedError
    def revoke(self, person_id, facts): raise NotImplementedError
    def forget(self, person_id): raise NotImplementedError
    def read_back(self, person_id): raise NotImplementedError
    def ask(self, asker_id, question, about_id): raise NotImplementedError
    def teardown(self): ...


class NoMemory(Adapter):
    """Baseline: nothing is stored, so nothing can leak and nothing is known."""
    name = "no-memory"

    def write(self, person_id, facts): pass
    def revoke(self, person_id, facts): pass
    def forget(self, person_id): pass
    def read_back(self, person_id): return set()
    def ask(self, asker_id, question, about_id): return set()


class Stub(Adapter):
    """Placeholder for a planned backend. Every call raises NotImplementedError."""

    def __init__(self, name):
        self.name = name

    def setup(self):
        raise NotImplementedError(f"{self.name} adapter is not implemented yet")


@dataclass(frozen=True)
class Backend:
    name: str
    group: str
    status: str
    factory: object = None

    def make(self):
        return self.factory() if self.factory else Stub(self.name)


GROUPS = ("baseline", "search_vector", "memory_layer", "graph_knowledge", "built_into_apps")

REGISTRY = {b.name: b for b in [
    Backend("no-memory", "baseline", READY, NoMemory),
    Backend("pgvector", "search_vector", READY, lambda: __import__("ctxlayer.pgvector_adapter", fromlist=["x"]).PgVector()),
    Backend("qdrant", "search_vector", PLANNED),
    Backend("weaviate", "search_vector", PLANNED),
    Backend("pinecone", "search_vector", PLANNED),
    Backend("langmem", "memory_layer", PLANNED),
    Backend("mem0", "memory_layer", PLANNED),
    Backend("letta", "memory_layer", PLANNED),
    Backend("redis", "memory_layer", PLANNED),
    Backend("loom", "memory_layer", PLANNED),
    Backend("neo4j", "graph_knowledge", READY, lambda: __import__("ctxlayer.neo4j_adapter", fromlist=["x"]).Neo4j()),
    Backend("relate", "graph_knowledge", READY, lambda: __import__("ctxlayer.relate_adapter", fromlist=["x"]).Relate()),
    Backend("cognee", "graph_knowledge", PLANNED),
    Backend("graphiti", "graph_knowledge", PLANNED),
    Backend("chatgpt-app", "built_into_apps", HOSTED),
    Backend("claude-app", "built_into_apps", HOSTED),
    Backend("gemini-app", "built_into_apps", HOSTED),
]}


def get(name):
    try:
        return REGISTRY[name]
    except KeyError:
        raise SystemExit(f"unknown backend {name!r}; run: ctxlayer list-backends") from None
