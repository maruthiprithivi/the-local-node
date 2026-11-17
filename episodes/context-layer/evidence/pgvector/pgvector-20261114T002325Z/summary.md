# pgvector summary

Runs: 5

- `pgvector-20261114T002325Z-seed7-45a3db3-r1`
- `pgvector-20261114T002325Z-seed7-45a3db3-r2`
- `pgvector-20261114T002325Z-seed7-45a3db3-r3`
- `pgvector-20261114T002325Z-seed7-45a3db3-r4`
- `pgvector-20261114T002325Z-seed7-45a3db3-r5`

Read backs: 115/115 passed, 0 leaked facts, 0 missing facts (stale-access / read-back-after-delete, all runs).

## Trap axes (first run; all-run totals in trap_axes.csv)

| axis | passed | total | all runs |
|---|---|---|---|
| freshness | 2 | 2 | 10/10 |
| identity_permission | 2 | 4 | 10/20 |
| entity | 1 | 1 | 5/5 |
| meaning_flip | 0 | 2 | 0/10 |

## Latency (ms)

| op | n | p50 | p95 |
|---|---|---|---|
| read_back | 115 | 250.08 | 1111.89 |
| ask | 55 | 249.73 | 778.29 |
| write | 115 | 504.89 | 1432.33 |

Setup (container up to schema ready, adapter side): median 3.763 s over 5 runs.
Tokens added per trap answer (approximate, regex pieces): mean 7.2, max 11.
