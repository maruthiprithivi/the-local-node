# Build vs buy: the same LoRA, two ways

Fill this in after lessons 10 and 11. It helps you compare local and managed training
with results you measured yourself, so you can recommend a route to a team.

| | Fireworks managed (lesson 10) | MLX on my Mac (lesson 11) |
|---|---|---|
| base model | | |
| category accuracy: base → tuned | → | → |
| severity accuracy: base → tuned | → | → |
| p95 latency (tuned) | | |
| wall-clock: data → working endpoint | | |
| training cost | | $0 |
| serving cost | $/h dedicated (multi-LoRA can share) | $0, but one user and no SLA |
| data leaves my machine? | yes, to Fireworks | no |
| scales to 100 concurrent users? | yes (replicas, autoscale) | no |

**My recommendation for a customer like X:** …

**One-liner:** "I ran the same LoRA locally and managed. Local is free and private; managed
got me to a production endpoint in minutes and scales. Most teams prototype locally and ship managed."
