# pgvector JML evidence (people, then agents / MCP servers / skills)

Everything here is synthetic data from a real run against pgvector/pgvector:0.8.0-pg17 (pg 17.6, extension 0.8.0, arm64)
in an isolated, loopback-only container with a random throwaway password, torn down after each batch.

| batch | dev commit | what | runs |
|---|---|---|---|
| pgvector-20261114T002325Z | 7336bf5 | baseline: people traps (10 probes) plus agent/MCP rows already in the workload | 5 |
| pgvector-20261114T022701Z | 48f2851 | full workload with 13 added non human trap asks, results split per subject kind | 5 |

One command (from episodes/context-layer): `REMOTE=<ssh alias of a Docker host> N=5 ./tools/repro_pgvector.sh` (empty REMOTE = local Docker).
Raw per-run JSONL, CSVs (trap_probes, trap_axes, trap_axes_by_kind, readbacks, readbacks_by_kind, latency_ms) and charts sit in each batch folder.

## Results of the pgvector-20261114T022701Z batch (5 runs, all-run totals)
- Read-back-after-delete (stale access): 115/115 pass, 0 leaked facts. Human 40/40, agent 35/35, MCP server 20/20, skill 20/20.
- freshness: 100% for every kind (an owner or scope change shows up immediately; removed entities answer empty).
- entity: 100% for every kind, but pgvector is keyed by entity ID, so this passes by construction (caveat, not a smart result).
- identity_permission: human 5/15, agent 10/10, MCP server 0/5, skill 0/5. The agent 10/10 is NOT identity enforcement:
  those probes ask after the agent's data was already deleted, so empty is trivially right. Where data still exists
  (MCP server, skill, active people) pgvector ignores who asks and leaks.
- meaning_flip: 0/20 for every kind (deleted or replaced facts cannot answer "no longer").
- Latency is dominated by the ssh tunnel (~240 ms p50); not DB speed. Not measured: crash durability.

## Media (media/)
- terminal_setup_and_run_1080p.mp4 (+ .cast): clean checkout of 7336bf5, setup and the live 1 run repro. 1920x1080.
- terminal_nonhuman_run_1080p.mp4 (+ .cast): tests plus the live 5 run pgvector-20261114T022701Z batch. 1920x1080. No hostnames, keys or IPs appear (checked by grep on the casts).
- shot_*.png: renders of real output files (summary.md, readbacks.csv, trap_probes.csv, run metadata). They are not desktop captures.
- whiteboard_pgvector_jml.png: one focal path (event, write/delete, read back, trap ask).
- Rebuild: cast2mp4.py, shot.py, whiteboard.py (pyte + Pillow).

## Clean clone repro check (repro-check/)
- `pgvector-20261117T165951Z`: a fresh clone of this kit in an empty temp directory, then `N=5 ./tools/repro_pgvector.sh`
  with local Docker (same image digest, amd64 this time). Exit 0. Read backs 115/115, 0 leaked facts; trap_axes.csv and
  trap_axes_by_kind.csv are byte-identical to `pgvector-20261114T022701Z`, and readbacks.csv and trap_probes.csv match
  row for row once run IDs and latency columns are set aside. Latency differs (no ssh tunnel here).
