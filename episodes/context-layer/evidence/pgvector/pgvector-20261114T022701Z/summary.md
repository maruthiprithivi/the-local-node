# pgvector summary

Runs: 5

- `pgvector-20261114T022701Z-seed7-48f2851-r1`
- `pgvector-20261114T022701Z-seed7-48f2851-r2`
- `pgvector-20261114T022701Z-seed7-48f2851-r3`
- `pgvector-20261114T022701Z-seed7-48f2851-r4`
- `pgvector-20261114T022701Z-seed7-48f2851-r5`

Read backs: 115/115 passed, 0 leaked facts, 0 missing facts (stale-access / read-back-after-delete, all runs).

## Trap axes (first run; all-run totals in trap_axes.csv)

| axis | passed | total | all runs |
|---|---|---|---|
| freshness | 7 | 7 | 35/35 |
| identity_permission | 3 | 7 | 15/35 |
| entity | 4 | 4 | 20/20 |
| meaning_flip | 0 | 4 | 0/20 |

## Read backs by subject kind (all runs)

| kind | passed | total | leaked facts |
|---|---|---|---|
| human | 40 | 40 | 0 |
| agent | 35 | 35 | 0 |
| mcp_server | 20 | 20 | 0 |
| skill | 20 | 20 | 0 |

## Probes by axis and subject kind (all runs; a trap can have two probes)

| axis | kind | passed | total |
|---|---|---|---|
| freshness | human | 10 | 10 |
| freshness | agent | 15 | 15 |
| freshness | mcp_server | 15 | 15 |
| freshness | skill | 15 | 15 |
| identity_permission | human | 5 | 15 |
| identity_permission | agent | 10 | 10 |
| identity_permission | mcp_server | 0 | 5 |
| identity_permission | skill | 0 | 5 |
| entity | human | 5 | 5 |
| entity | agent | 5 | 5 |
| entity | mcp_server | 5 | 5 |
| entity | skill | 5 | 5 |
| meaning_flip | human | 0 | 5 |
| meaning_flip | agent | 0 | 5 |
| meaning_flip | mcp_server | 0 | 5 |
| meaning_flip | skill | 0 | 5 |

## Latency (ms)

| op | n | p50 | p95 |
|---|---|---|---|
| read_back | 115 | 240.08 | 786.57 |
| ask | 130 | 243.26 | 808.02 |
| write | 115 | 499.03 | 1341.17 |

Setup (container up to schema ready, adapter side): median 3.046 s over 5 runs.
Tokens added per trap answer (approximate, regex pieces): mean 6.8, max 15.
