# The race for the context layer: test harness

One provider agnostic harness for every episode of the series. Each backend (a vector store, a memory
layer, a graph, or the memory built into an app) runs the same synthetic join, move, leave workload,
and after every change the harness reads memory back instead of trusting the delete.

Everything in `workload/jml.yaml` is made up: the company, the people, the agents, MCP servers and skills,
and the access names.

## One command

From a clean checkout, with Docker and Python 3.11 or newer:

```bash
cd episodes/context-layer
N=5 ./tools/repro_pgvector.sh
```

It installs the dependencies into a local `.venv` (pinned in `requirements.txt`, plus `matplotlib==3.9.2`
for the charts), starts the pinned `pgvector/pgvector:0.8.0-pg17` image on loopback with a throwaway password, runs
the seed 7 workload N times, writes raw JSON lines, CSVs, charts and `summary.md` under `evidence/pgvector/<batch>/`,
and tears everything down. Run IDs end in the short commit of your checkout. The committed batches in
`evidence/pgvector/` are the episode's own runs; `evidence/pgvector/README.md` lists what each one is.

What this kit covers: the harness, the `no-memory` baseline and the pgvector episode, with raw outputs, CSVs and
charts. The `relate` and `neo4j` adapters and scripts are included so you can run them; their results ship with
their own episode.

## What is here

| path | what it is |
|---|---|
| `workload/jml.yaml` | the synthetic workload: people who join, move and leave, non human entities that are added, changed and removed, plus the trap asks |
| `ctxlayer/adapters.py` | the backend registry. `no-memory`, `pgvector`, `relate` and `neo4j` (Community server) run; every other entry is a stub that is not implemented yet |
| `ctxlayer/traps.py` | the four trap axes: `freshness`, `identity_permission`, `entity`, `meaning_flip` |
| `ctxlayer/plan.py` | builds the plan; every write, revoke or forget is followed by a read back |
| `ctxlayer/runner.py` | executes a plan against a ready backend and writes raw outputs as JSON lines |
| `tests/` | checks the read back rule, the trap axes, the example person and the baseline run |

## Run it

Python 3.11 or newer. Dependencies are pinned in `requirements.txt` and `pyproject.toml`.

```bash
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests

.venv/bin/ctxlayer list-backends
.venv/bin/ctxlayer plan --backend pgvector --person E1001 --dry-run
.venv/bin/ctxlayer plan --backend pgvector --entity A2002 --dry-run
.venv/bin/ctxlayer run --backend no-memory
```

`plan` only prints. It never starts a backend, never writes, and prints no timings or results.
`run` refuses any backend that is not `ready`.

## The example person

`E1001 Mira Okafor` joins support with `ticket_queue` and `support_kb`, moves to finance (support
access revoked, `ledger_read` and `expense_review` granted), then leaves. After she leaves, the right
answer about her access is that she has none. `E1011 Mira Okoro` exists for the entity trap.

## Non human lifecycle

Every entity has a `kind`: `human`, `agent`, `mcp_server` or `skill`. Humans `join`, `move` and `leave`.
Agents, MCP servers and skills are `add`ed, `change`d (a scope or an owner change) and `remove`d, or lose
everything through `owner_leaves` when their human owner leaves. An owner is stored as the fact
`owner:<id>`, so an owner change is a revoke and a write, and each gets its own read back. The trap axes
apply to them too.

| id | kind | lifecycle |
|---|---|---|
| `A2001` support triage agent | agent | added for E1001, owner handed to E1011, removed |
| `A2002` release notes agent | agent | added for E1002, scope widened, owner E1002 leaves |
| `M3001` ledger MCP server | mcp_server | added, tool swapped for a redacted one, removed |
| `S4001` expense summary skill | skill | added, owner handed from E1003 to E1001, removed |

## The five measures

`correctness` (right facts after each step), `stale_leak` (old roles and leavers that come back),
`read_latency` (read time, with run count), `tokens_added` (tokens memory adds to a prompt) and
`setup_steps` (setup steps to first query).

## Reproducibility

The workload carries its own `seed`. Raw outputs from `run` go to `results/` (one JSON line per step).

## pgvector baseline (people and non human cases)

One command, from a clean checkout (needs docker, local or over ssh):

```bash
REMOTE=<ssh alias, or empty for local docker> N=5 ./tools/repro_pgvector.sh
```

It checks load first (refuses at 85%, aborts at 95%), starts `pgvector/pgvector:0.8.0-pg17` with a random
throwaway password (never printed), loopback only, 2 GB and 2 CPUs, runs the workload N times with run IDs
`pgvector-<UTC time>-seed7-<git sha>-r<n>`, scores every trap probe, writes CSVs, charts and `summary.md`
under `evidence/pgvector/<batch>/`, and removes the container (and the image if it pulled it).

How traps are scored: each trap carries `probes`, asks that fire right after a named event's read back,
with ground truth written in `workload/jml.yaml` (not derived from the backend). A trap passes when all its
probes pass; each axis is reported alone.

Caveats that go with any number from this baseline:
- Latency was measured from a client reaching the database through an ssh tunnel (about 250 ms round trip), so it
  is mostly network, not pgvector. Use it for relative cost only; do not quote it as database speed.
- The `entity` trap hands the adapter the entity ID, so it tests ID keyed lookup, not name resolution. A harder
  name resolution variant is a follow up.
- `tokens_added` is an approximation (regex pieces of the rendered answer), not a model tokenizer.
- The embeddings are deterministic hashes, not a language model, so ranking is not semantic; with at most five
  facts per entity every fact is returned. This baseline measures the access control and lifecycle behaviour of a
  plain vector store, not retrieval quality.
- Durability across a crash and the pgvector crash case are not measured here.

## neo4j (Community server) run (self-install comparison)

```
N=1 ./tools/repro_neo4j.sh
```

Hand-built adapter for comparing a Neo4j (server) self-install attempt.
Same pinned Community image, graph model and driver as relate, but
registered as `neo4j`. One JML run is enough for the comparison.
CPU-only container, torn down afterwards. This is not
the Relate episode (media, direct-path latency and crash
durability belong there). No neo4j results ship in this kit yet.

## relate (Neo4j) run (people and non human cases)

```
REMOTE=<ssh alias, or empty for local docker> N=5 ./tools/repro_relate.sh
```

Same load guard, workload, seed, read backs, traps and report as pgvector. Starts the pinned
`neo4j:2026.10.2-community@sha256:4a2fd4f4...` (the DBMS Neo4j Desktop / Relate runs, file mode) with a random
password kept only in the gitignored `.secrets/relate.env`, and tears it all down. The adapter and scripts are
here so you can run it today; the Relate results, crash durability check and media ship with the Relate episode.
