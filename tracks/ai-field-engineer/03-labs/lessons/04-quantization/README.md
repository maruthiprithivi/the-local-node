# 04 · Quantization: size, speed, quality

> **Lab book:** Local labs → **L4** · Ceiling calculator  **Watch:** video 4 `04-quantization.mp4`, video 3 `03-gpu-bandwidth.mp4`
> **Time:** 45 min  **Cost:** free (≈17 GB download)

## What and why

Quantization stores each weight in fewer bits: 16 → 8 → 4. Think of it as a photo saved
at lower JPEG quality. The file is smaller and loads faster, and past a certain point
you notice the blur.

Decode reads every weight once per token, so fewer bytes means proportionally more tokens:

```
decode ceiling (tok/s) ≈ memory bandwidth (GB/s) ÷ model size (GB)

M4 Max 546 GB/s ÷ 8B @ Q8 (8.5 GB)  ≈  64 tok/s
M4 Max 546 GB/s ÷ 8B @ Q4 (4.9 GB)  ≈ 111 tok/s      ← same model, ~1.7× faster
```

Real engines reach 60–85% of that ceiling. Prefill barely changes with quantization
because it is compute-bound. That contrast is the whole lesson.

## Read the code first

- `quant_bench.sh`: `llama-bench` runs the engine with no server, so you measure the engine alone.
- `ceiling_check.py`: the formula above in six lines, printed next to what you measured.
- `quality_check.py`: 12 questions as a smoke alarm for the quality cliff.

## Run

```bash
cd lessons/04-quantization
python ceiling_check.py --demo                 # see the shape first, no download

bash quant_bench.sh                            # downloads Q8_0, Q4_K_M, Q3_K_M and benches them

for q in Q8_0 Q4_K_M Q3_K_M; do                # quality per quant
  bash ../02-three-local-servers/serve_llamacpp.sh $q & sleep 20
  python quality_check.py --target llamacpp --label $q
  kill %1
done
```

## What you should see

```
quant   size_gb  pp512    tg128  ceiling  efficiency_%
Q8_0        8.5  1,150     52.0     64.2          81.0
Q4_K_M      4.9  1,050     86.0    111.4          77.2    ← decode ×1.65, prefill ~same
Q3_K_M      4.0    980     98.0    136.5          71.8
```

Quality usually holds at Q8 and Q4_K_M, and Q3 starts dropping the multi-step and
format questions first.

## Check yourself

1. Why does halving the bytes nearly double decode but not prefill? *(Decode is bandwidth-bound; prefill is compute-bound.)*
2. Where does FP8 on an H100 fit in? *(Same idea in hardware. H100/H200 have FP8 tensor cores, and Blackwell adds NVFP4, so the compute also speeds up rather than just memory.)*
3. The customer is worried about quality. What do you do? *(Run their own 50-prompt eval at each precision and show the quality, latency and cost table from lesson 09.)*

## Explain what you learned

> "Decode speed is bandwidth over bytes per token. Quantization changes the denominator.
> I never recommend a precision without running the customer's own eval at that precision."

**Next →** [05 · KV cache](../05-kv-cache/)
