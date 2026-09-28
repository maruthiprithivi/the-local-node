# Field Engineer explainers — 18 narrated videos

Eighteen short explainer videos covering everything an AI Field Engineer / Solutions Architect is
expected to hold in their head, from prefill and decode through to multi-node serving. Built with
**Remotion 4.0.527** (React → MP4) and **Kokoro-82M** (Apache-2.0 TTS). No paid APIs anywhere.

Each video: a title card with what you'll learn → concept scenes → worked examples with real numbers
(before/after comparisons, sizing maths) → a "run it" scene with the actual commands → a three-point
recap → an end card naming the lab to run next. Subtitles are burned in,
in a reserved band that the diagrams never draw into.

| # | id | covers | pairs with lab |
|---|---|---|---|
| 1 | `inference-101` | prefill, decode, TTFT, ITL, goodput | F1 |
| 2 | `kv-cache` | KV maths, PagedAttention, FP8 KV | L5 |
| 3 | `gpu-bandwidth` | roofline, decode ceiling, device table | L3 · L4 |
| 4 | `quantization` | FP16 → FP8 → 4-bit, KV quantization | L4 |
| 5 | `batching` | continuous batching, chunked prefill, speculation | L3 |
| 6 | `training` | SFT, LoRA, DPO, RFT — and how to choose | F5 · L8 |
| 7 | `offloading` | sizing formula, offload order, MoE, TP vs PP | L7 |
| 8 | `platform` | serving layers, capacity modes, maturity curve | capstone |
| 9 | `serving-stack` | what an inference server does; containers; the five flags | L2 · L9 |
| 10 | `benchmarking` | traffic profiles, concurrency sweeps, percentiles | L3 |
| 11 | `prefix-caching` | shared prefixes, RadixAttention, prompt caching | L6 · F2 |
| 12 | `qlora` | frozen 4-bit base + adapter, data and evals | L8 |
| 13 | `scale-out` | speculation, acceptance rate, two-box reality | L9 |
| 14 | `full-finetuning` | training loop, 16 B/param, ZeRO/FSDP, when full FT pays | T1 · T2 |
| 15 | `sft` | data format, loss masking, data volume, knobs, loss curves | T2 |
| 16 | `peft` | LoRA B·A maths, QLoRA, DoRA, adapters, prefix tuning, IA³, multi-LoRA | T2 |
| 17 | `rlhf` | preferences, reward model, PPO, KL leash, reward hacking, GRPO/RFT | T1 |
| 18 | `dpo` | the DPO loss, one worked step, pairs from product data, IPO/KTO/ORPO | T3 |

Total ≈ 57 minutes (videos 1–13 ≈ 2.5–3 min each; the training deep dives 14–18 ≈ 4 min each).
Every end card names the repo lesson and lab to run next (`field-engineer-labs/lessons/NN-*`).

## Regenerate on your Mac (MLX)

```bash
npm install
npx remotion browser ensure

pip install mlx-audio misaki soundfile numpy
python scripts/tts_mlx.py                      # all 18, voice af_heart, speed 0.96
python scripts/tts_mlx.py --video kv-cache --voice am_michael

npm run dev                                    # Remotion Studio
npm run render                                 # out/<id>.mp4
```

`scripts/tts_patch.py --video <id> --scenes last` re-voices only the scenes you edited.
`scripts/tts_onnx.py` is the same script for a Linux/CPU box (kokoro-onnx + weights from the
kokoro-onnx GitHub releases). It produced the delivered MP4s.

## How it fits together

- `src/narration.json` — single source of truth: every video, scene, visual and narration line.
  Both TTS scripts and the compositions read it.
- `scripts/tts_*.py` — write `public/audio/<id>/NN.wav` (24 kHz) plus `public/scenes/<id>.json`
  with the measured duration of each scene, a 0.35 s lead-in and a 0.7–1.1 s tail for pacing.
- `src/Root.tsx` — `calculateMetadata` reads those durations, so composition length always matches
  the real audio. With no audio present it falls back to a word-count estimate, so the Studio works
  before you run TTS.
- `src/Explainer.tsx` — layout: header, visual stage, **200px subtitle band**, progress bar.
  Subtitles come from `src/lib/subtitles.ts`, which splits narration into sentence-sized cues and
  times them by character count across the scene.
- `src/components/Visuals.tsx` — every diagram. Each one takes `p` (scene progress 0→1) so the
  animation fills whatever length the narration turns out to be.
- `src/theme.ts` — colours, fonts, fps (24).

## Rendering notes

- Delivered files are 1248×702 (`--scale=0.65`) h264. Drop the scale flag for full 1920×1080.
- `npx remotion browser ensure` downloads Chrome Headless Shell; on arm64 Linux only the headless
  shell is available, which is what Remotion uses anyway.
- Remotion bundles FFmpeg — don't install one.
- Licence: Remotion is free for individuals and companies up to 3 people; CI rendering counts as an
  automation under their terms. Kokoro-82M is Apache-2.0.
