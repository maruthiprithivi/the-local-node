# Session-log replay kit

Replays coding-agent session logs and counts how often a final "done" message hid
an error, a retry, or a test that never ran. Built for one log set (about 1,000
sessions from several local models and agent harnesses), written so it can be re-run
on that set or pointed at a similar one.

* `DEFINITIONS.md`: what counts as a done claim, a hidden error, a hidden retry and an
  unrun test. Written before counting; every later change is listed with its reason.
* `results.md` / `results.json`: the counts, with denominators, by model, harness,
  task set and task.
* `validation.csv`: 109 sessions read by hand, with the reader's truth per flag; `--score`
  re-derives the verdicts from the latest run and writes `out/validation_score.json`.
* `judgments.jsonl`: every local-model answer behind `results.json` (465), keyed by prompt
  hash, without the prompts. Enough for `run.py --offline` to reproduce `results.json`
  byte for byte, given the logs.

## What is not in this folder

The raw logs. They contain host names, internal paths and user names, so they are
not published. `out/` (per-session rows, model prompts and answers, reading sheets)
is generated from the logs and is not published either; `judgments.jsonl` is its
prompt-free extract. Session ids in
`validation.csv` and `results.md` are the first 8 hex digits of the SHA-1 of the
original id.

## Layout

```
run.py              normalize every session, detect, ask the local model, aggregate
replay/parsers.py   one parser per log format -> one event list per session
replay/load.py      manifest loading, dedup, scope (main / aider / excluded), grouping
replay/detect.py    deterministic detectors (claims, failures, retries, unrun tests)
replay/judge.py     local-model judgments, cached by prompt hash, every call logged
replay/validate.py  seeded sample for hand reading, and scoring of validation.csv
replay/recover.py   re-extract sessions the log packer overwrote (see below)
replay/ship_judgments.py  write judgments.jsonl from out/llm_judgments.jsonl
```

Formats handled: Qwen Code chat JSONL, omp JSONL, dsh `agent.log`, dsh session v4,
pi / SoL-Pi request JSONL, an OpenShell agent's JSON, and Aider polyglot transcripts.

## Re-running

Requirements: Python 3.11+. `zstandard` only for the recovery step. A local
OpenAI-compatible endpoint for the model judgments (we used a 27B model with thinking
off, temperature 0, seed 0, at most 2 calls in flight).

```bash
# 0. logs/ next to kit/, with MANIFEST.csv (session_id, run_set, model, harness,
#    task_set, task, fmt, dest_path, ...)

# 1. one-time: recover sessions the packer overwrote (17 in our set)
python -m replay.recover --runs <dir with the original run archives>

# 2. full run: deterministic detectors + model calls for ambiguous cases
REPLAY_LLM_URLS=http://127.0.0.1:8000/v1/chat/completions \
REPLAY_LLM_BLACKOUT="" \
python3 run.py --workers 2

# 2b. write the shippable, prompt-free judgment log (judgments.jsonl)
python3 -m replay.ship_judgments

# 3. exact replay from the logged model answers, no endpoint needed
python3 run.py --offline

# 4. draw the hand-check sample (seed 23), read it, fill validation.csv, score it
python3 -m replay.validate
python3 -m replay.validate --score
```

`--offline` fails loudly on any judgment that is not in `out/llm_judgments.jsonl` or the
shipped `judgments.jsonl`, so a changed prompt or detector cannot silently reuse old
answers. The model calls are not perfectly repeatable: re-asking them online at
temperature 0 moved a few of our counts by one or two sessions (see DEFINITIONS.md,
Repeatability). `results.json` is tied to `judgments.jsonl`.

## Known limits

See "What this cannot measure" in `results.md`. The main ones: it checks what the
agent said against what its own log shows, not whether the code is right; harnesses
that print exit codes only on failure make every silent step an inferred exit 0; and
the model that judges whether a final message disclosed a retry over-credits
disclosure, so the hidden-retry count is reported as a range.
