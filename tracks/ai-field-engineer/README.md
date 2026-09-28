# AI Engineering Field Kit: start here

> **Got this as 11 parts (`fw-kit-part01-of-11.zip` … `part11`)?** Put them in one folder and
> unzip them all into the same place. They fill in one `fireworks-field-engineer-kit/` folder:
> ```bash
> cd ~/Downloads && for f in fw-kit-part*-of-11.zip; do unzip -oq "$f"; done
> ```
> (Double-clicking each one in Finder makes separate "… 2", "… 3" folders, so use the command above.)

Hands-on material for learning AI engineering and field engineering, in one folder.
It has three parts that work together, plus the source for the videos:

```
fireworks-field-engineer-kit/
├── 01-videos/        18 narrated explainers, numbered 01–18 (watch)
├── 02-lab-book/      the lab book web page + the earlier field guide (read)
├── 03-labs/          the code: lessons 00–18, one folder per lesson (run)
└── 04-video-source/  Remotion + Kokoro project that made the videos (optional)
```

**The loop for every topic:** watch the video (3–4 min) → read the matching lab card in the
lab book → `cd 03-labs/lessons/NN-…`, read its README, run the scripts. Your numbers land in
`03-labs/results/`, and lesson 15 turns them into a customer sizing memo.

---

## Get started in 5 steps (about 15 minutes, nothing to download)

1. **Open the lab book.** Double-click `02-lab-book/field-engineer-lab-book.html`. Keep it on the left of your screen.
2. **Watch** `01-videos/01-inference-101.mp4`.
3. **Set up the code** in a terminal on the right:
   ```bash
   cd fireworks-field-engineer-kit/03-labs
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt && pip install -e .
   cp .env.example .env
   ```
4. **Check it all works offline**, using a built-in fake model server:
   ```bash
   make mock &          # fake LLM server on :9000
   make smoke           # runs every lesson end to end, ~2 min, should end "✓ smoke test passed"
   ```
5. **Start lesson 00:** `bash lessons/00-setup/setup_mac.sh` installs Ollama, llama.cpp and MLX. Then follow the table below.

Fireworks costs money only in the lessons marked **$**. Run `make fw-check` after each one
to confirm nothing is still billing.

---

## The course, in order

Watch the video(s), then do the lesson. Lesson folders are in `03-labs/lessons/`.

### Part 1: Serving and inference (days 1–10)

| day | watch (`01-videos/`) | then do (`03-labs/lessons/`) | lab card | cost |
|---|---|---|---|---|
| 1 | `01-inference-101.mp4` · `09-serving-stack.mp4` (first half) | `00-setup` → `01-latency-harness` | L1 · F1 | ~$0.02 |
| 2 | `09-serving-stack.mp4` | `02-three-local-servers` | L2 | free |
| 3 | `10-benchmarking.mp4` · `05-batching.mp4` · `03-gpu-bandwidth.mp4` | `03-concurrency-sweep` | L3 | free |
| 4 | `04-quantization.mp4` · `02-kv-cache.mp4` | `04-quantization` → `05-kv-cache` | L4 · L5 | free |
| 5 | `11-prefix-caching.mp4` | `06-prefix-caching` | L6 · F2 | ~$0.03 |
| 6 | `08-platform.mp4` | `07-structured-output` → `08-batch-api` | F3 · F4 | ~$0.03 |
| 7 | `06-training.mp4` · `12-qlora.mp4` | `09-eval-harness` → `10-lora-fireworks` | F6 · F5 | **$** ~1 GPU-h |
| 8 | `12-qlora.mp4` | `11-lora-local-mlx` | L8 | free |
| 9 | `07-offloading.mp4` · `13-scale-out.mp4` | `12-moe-vs-dense` → `13-speculative-decoding` → `14-spark-track` | L7 · F7 · L9 | **$** ~½ GPU-h |
| 10 | `08-platform.mp4` (again) | `15-capstone` | Capstone | free |

### Part 2: How models are trained (days 11–12)

| day | watch (`01-videos/`) | then do (`03-labs/lessons/`) | lab card | cost |
|---|---|---|---|---|
| 11 | `14-full-finetuning.mp4` · `15-sft.mp4` · `16-peft.mp4` | `16-training-toy` (part 1) → `17-full-vs-peft-mlx` | T1 · T2 | free |
| 12 | `17-rlhf.mp4` · `18-dpo.mp4` | `16-training-toy` (part 2) → `18-preference-dpo` | T1 · T3 | free · **$** optional |

---

## The 18 videos

Numbers match the "Video N of 18" on each title card and the "Watch:" line in each lesson README.

| # | file | min | what it explains | run next |
|---|---|---|---|---|
| 01 | `01-inference-101.mp4` | 3:02 | prefill vs decode, TTFT, ITL, throughput, goodput | lesson 01 |
| 02 | `02-kv-cache.mp4` | 3:02 | KV cache maths, PagedAttention, FP8 KV | lesson 05 |
| 03 | `03-gpu-bandwidth.mp4` | 3:10 | roofline, decode ceiling = bandwidth ÷ bytes | lessons 03–04 |
| 04 | `04-quantization.mp4` | 2:43 | FP16 → FP8 → 4-bit, NVFP4, KV quantization | lesson 04 |
| 05 | `05-batching.mp4` | 2:58 | continuous batching, chunked prefill, speculation | lessons 03, 13 |
| 06 | `06-training.mp4` | 3:14 | overview: SFT, LoRA, DPO, RFT and how to choose | lessons 10–11 |
| 07 | `07-offloading.mp4` | 3:07 | sizing, offloading, MoE, tensor vs pipeline parallel | lesson 12 |
| 08 | `08-platform.mp4` | 2:51 | serving layers, capacity modes, maturity curve | lesson 15 |
| 09 | `09-serving-stack.mp4` | 2:56 | what an inference server does, containers, key flags | lessons 02, 14 |
| 10 | `10-benchmarking.mp4` | 2:22 | traffic profiles, concurrency sweeps, percentiles | lesson 03 |
| 11 | `11-prefix-caching.mp4` | 2:37 | shared prefixes, RadixAttention, prompt caching | lesson 06 |
| 12 | `12-qlora.mp4` | 2:49 | 4-bit base + adapter on your own box | lessons 11, 10 |
| 13 | `13-scale-out.mp4` | 2:41 | speculative decoding, acceptance rate, two boxes | lessons 13–14 |
| 14 | `14-full-finetuning.mp4` | 4:17 | training loop, 16 bytes/param, ZeRO/FSDP, when full FT pays | lesson 17 |
| 15 | `15-sft.mp4` | 4:02 | data format, loss masking, data volume, loss curves | lesson 17 |
| 16 | `16-peft.mp4` | 3:50 | LoRA maths, QLoRA, DoRA, adapters, IA³, multi-LoRA | lesson 17 |
| 17 | `17-rlhf.mp4` | 4:10 | reward model, PPO, KL leash, reward hacking, GRPO/RFT | lesson 16 |
| 18 | `18-dpo.mp4` | 3:50 | the DPO loss, a worked step, pairs from product data | lesson 18 |

Total ≈ 57 minutes. The subtitles are burned in.

## The 19 lessons (`03-labs/lessons/`)

| # | folder | what you do | runs on |
|---|---|---|---|
| 00 | `00-setup` | install Ollama, llama.cpp, MLX; Fireworks guardrails | Mac |
| 01 | `01-latency-harness` | measure TTFT and ITL; the harness every later lesson reuses | Mac → FW |
| 02 | `02-three-local-servers` | one model served by Ollama, llama.cpp and MLX | Mac |
| 03 | `03-concurrency-sweep` | the throughput vs TTFT curve that sizes a deployment | Mac |
| 04 | `04-quantization` | Q8 vs Q4 vs Q3: speed, ceiling maths, quality check | Mac |
| 05 | `05-kv-cache` | KV cache maths, then break and fix long context | Mac |
| 06 | `06-prefix-caching` | shared prefixes: the ~20× TTFT win, and the anti-pattern | Mac → FW |
| 07 | `07-structured-output` | JSON validity: prompt vs json_object vs json_schema | Mac → FW |
| 08 | `08-batch-api` | evals at half price with the Batch API | FW |
| 09 | `09-eval-harness` | quality + p95 + $/1k tasks in one table, LLM judge | Mac → FW |
| 10 | `10-lora-fireworks` | a real LoRA fine-tune: train → deploy → eval → **delete** | FW **$** |
| 11 | `11-lora-local-mlx` | the same LoRA on your Mac (QLoRA) | Mac |
| 12 | `12-moe-vs-dense` | infer MoE active parameters from decode speed | Mac |
| 13 | `13-speculative-decoding` | draft models, acceptance rate, when it hurts | Mac → FW **$** |
| 14 | `14-spark-track` | vLLM and SGLang on the DGX Spark, same harness | Spark |
| 15 | `15-capstone` | build the customer sizing memo from your results | anywhere |
| 16 | `16-training-toy` | full vs LoRA, SFT → reward model → RLHF vs DPO, in numpy | anywhere |
| 17 | `17-full-vs-peft-mlx` | full vs LoRA vs DoRA on a real model; data checker | Mac |
| 18 | `18-preference-dpo` | DPO on your Mac (and optionally Fireworks) | Mac → FW |

Every lesson folder has a `README.md` with the same parts: what and why, the code to read first,
commands to run, expected output, self-check questions and a short explanation of the result.

## What's in 02-lab-book

- `field-engineer-lab-book.html` is the main companion page. It covers the role, what Fireworks sells, spend control, all lab cards (F1–F7, L1–L9, T1–T3, each naming its lesson folder), calculators, your handbook mapped to practice, the 12-day plan and talk tracks. It works offline; a hosted copy is also in your Claude artifacts.
- `inference-field-guide.html` is the earlier visual field guide, with interactive explainers and the frameworks chapter.

## What's in 04-video-source (optional)

This is the Remotion project that rendered the videos. Use it to change a script, the voice or
the pacing. On your Mac:

```bash
cd 04-video-source && npm install && npx remotion browser ensure
pip install mlx-audio misaki soundfile numpy
python scripts/tts_mlx.py                 # regenerate narration with Kokoro on MLX
npm run render                            # → out/<id>.mp4
```

## If something doesn't work

| symptom | fix |
|---|---|
| `make smoke` says connection refused | the mock isn't running: `make mock &` first |
| a lesson says `Connection refused` | that server isn't running; `make check` shows what is up |
| a Fireworks model id is not found | ids change; copy a current one from the model library and pass `--model` |
| page shows odd symbols | open the `.html` in a browser, not a text editor |
| unsure whether you're still paying | `make fw-check` lists anything still billing |
