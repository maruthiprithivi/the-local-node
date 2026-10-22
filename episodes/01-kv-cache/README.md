# Episode 1: why your 8B model runs out of memory

This folder is the live demo for the episode. Clone the repo, open this folder, and run the same commands on your own machine. The weights stay one size. The KV cache grows with every token, and it grows again with every parallel chat.

The calculator reads the real shape (layers, KV heads, head dim, dtype) and prints the formula. The measurement script asks a local Ollama server for the memory it reports at several context lengths, plus the time to the first token. The chart draws those two series.

Run everything below from this folder.

## What you need

### Mac

- macOS on Apple Silicon
- [Ollama](https://ollama.com) installed, with the app or `ollama serve` already running
- Python 3.11 or newer

### DGX Spark-class Linux box

- Linux with an NVIDIA GPU
- Ollama installed and running
- Python 3.11 or newer
- `nvidia-smi` on `PATH` if you want the GPU column. If `memory.used` is `[N/A]`, each row sums compute-apps for the runner that appeared for this model. The script still finishes without `nvidia-smi`.

The chart also needs Node.js 22 or newer. You do not need it for the calculator or the measurement.

If `python` is missing, use `python3` in every command below.

## 1. Check the worked example

This does not download a model. It is the shape from the episode: 32 layers, 32 KV heads, head dim 128, 2 bytes, 8,192 tokens.

```bash
python kv_cache.py --example
```

You should see:

```text
formula: 2 x layers x kv_heads x head_dim x bytes x tokens
per token: 2 x 32 x 32 x 128 x 2 = 524288 bytes (512 KiB)
at 8192 tokens: 2 x 32 x 32 x 128 x 2 x 8192 = 4 GiB
```

The same shape with grouped query attention (32 attention heads sharing 8 KV heads) prints:

```text
at 8192 tokens: 2 x 32 x 8 x 128 x 2 x 8192 = 1 GiB
```

The table under each shape repeats the formula at `f16` (2 bytes), `q8_0` (1 byte) and `q4_0` (half a byte). At 8,192 tokens those three columns are 4 GiB, 2 GiB and 1 GiB. That is arithmetic, not a measurement of your machine. `q8_0` on Ollama needs flash attention.

A real config where `head_dim` is missing uses hidden size divided by attention heads. Qwen2.5 7B Instruct is 28 layers, 4 KV heads, hidden size 3584, so the head dim is 128. At 8,192 tokens the same command shape prints `0.4375 GiB`, which is 56 KiB per token. Four chats at 32,768 tokens is 7 GiB of cache:

```bash
python kv_cache.py --layers 28 --attention-heads 28 --kv-heads 4 --head-dim 128 --tokens 32768 --chats 4 --contexts 8192,32768
```

That printout says 56 KiB per token, 1.75 GiB for one chat at 32,768 tokens, and 7 GiB for four chats. It also says 28 KV heads, with no grouping, would be 49 GiB for those same four chats.

## 2. Point it at your model

One source at a time.

```bash
python kv_cache.py --ollama llama3.2:1b
python kv_cache.py --config config.json
python kv_cache.py --gguf model.gguf
```

`--ollama` calls Ollama's model info on localhost and reads `general.architecture`, the layer count, the attention-head count, and the KV-head count. If the file has no key length, head dim is the embedding length divided by the attention heads.

`--config` reads a `config.json`: `num_hidden_layers`, `num_attention_heads`, `num_key_value_heads`, and `head_dim`. A missing `head_dim` uses `hidden_size / num_attention_heads`. A multimodal file can keep those keys under `text_config`.

`--gguf` reads the same keys out of the GGUF metadata and stops before the tensor bytes.

Some models only keep a KV cache on some layers. A hybrid sets `full_attention_interval` (4 means one full-attention layer out of every four; the rest are linear or SSM and do not grow a cache with the context). `attention.recurrent_layers` in a GGUF, or `layer_types` in a config, names those layers one by one, and that list wins over the interval. Next-token prediction blocks (`nextn_predict_layers`, or `mtp_num_hidden_layers` on a config) are left out of the chat cache when they sit inside the block count. When the count is not smaller than the block count, the blocks are not in that list and are not subtracted. A config's `num_hidden_layers` is the trunk, so a separately listed MTP count is not subtracted from it. The formula then uses the full-attention count, and the report says how it got there. Sliding-attention layers still store K and V, so they are counted. The formula uses the full context you pass, which is larger than a short window.

Where the two head counts differ, the report prints the group size. That is grouped query attention: several query heads share one KV head, and the cache shrinks by that factor. You read it off the model. You do not switch it on.

A weight quantization such as `Q4_K_M` is printed separately. It does not change the cache width. The cache stays 2 bytes per value until you ask for another width:

```bash
python kv_cache.py --ollama llama3.2:1b --kv q8_0
```

## 3. Measure a local Ollama model

The default model is `llama3.2:1b`, a small one. The default contexts are 512, 1024, 2048, 4096 and 8192. The prompt stays one short line. Ollama sizes the cache from `num_ctx` when the model loads, so the script unloads the model between rungs and records the size the runtime reports after each load.

```bash
python measure_kv.py
```

Nothing is downloaded unless you pass `--pull`. If the default model is not installed yet:

```bash
python measure_kv.py --pull
```

A name that looks like 7B or larger is refused until you pass that same flag:

```bash
python measure_kv.py --model qwen2.5:7b --pull --contexts 1024,4096,8192
```

The script writes `runs/kv-sweep.json` and `runs/kv-sweep.csv`. Those files are local run output and are not part of the repo. Each row has:

| column | what it is |
| --- | --- |
| `predicted_kv_bytes` | the formula, cache only |
| `measured_runtime_bytes` | `size` from Ollama's process list. This is weights plus compute buffers plus the cache, not the cache alone |
| `measured_vram_bytes` | `size_vram` when Ollama reports it, otherwise empty |
| `gpu_memory_bytes` | `nvidia-smi` memory.used when that query returns a number. If it returns `[N/A]`, the row sums `nvidia-smi --query-compute-apps=pid,used_memory` for the runner serving this model: the PID Ollama reports, or the new runner PID after the load. Other resident runners are not added in |
| `gpu_attribution` | which of those approaches produced the GPU figure (`ollama-pid`, `new-pid`, `only-runner`, `memory.used`, or `unattributed`) |
| `process_rss_bytes` | on macOS, the Ollama server plus runners Ollama spawned. A standalone `llama-server` is left out unless its parent chain reaches Ollama. Omitted on Linux, because CUDA memory is not in the resident set and the number stays flat |
| `ttft_ms` | wall time to the first token on a second, already-loaded request. A thinking model's first thinking token counts. The request sends `think: false` when the server accepts it |
| `load_ms` | time to the first token on the request that loaded the model |

On a Mac the runtime size is the unified-memory figure. There is no separate GPU counter, and the JSON says so. On Linux, a missing `nvidia-smi` leaves `gpu_memory_bytes` empty and the sweep continues. A context the server refuses is one row with a note, not a failed run.

The measured total includes the weights and the compute buffers, not just the KV cache, so `measured_runtime_bytes` sits above `predicted_kv_bytes`. Ollama's reported model size is an estimate, and it moves in steps rather than with every extra token. Use the GPU figure, or the process growth between rungs, for the cache. Doubling the context doubles the predicted cache. That growth should show up on top of a size that stays put. A hybrid model's prediction only counts full-attention layers, so it will be smaller than a count of every block. The report prints both, for example `blocks: 65, KV layers: 16`, and the JSON shape carries `blocks` and `kv_layers`. A short attention window can still make the live growth smaller than that prediction.

Other models that are already loaded are unloaded before the sweep, so an older runner does not sit inside every GPU row. Pass `--keep-others` to leave them loaded. Each row's note says which attribution was used. The file-level note counts how many rows actually got a GPU figure, instead of repeating a probe from before the model was loaded.

To try a quantized cache, restart Ollama with `OLLAMA_KV_CACHE_TYPE=q8_0` (flash attention has to be on), then run the sweep again to a second file:

```bash
python measure_kv.py --out runs/kv-sweep-q8
```

`--out` is a prefix. `runs/kv-sweep-qwen3.8` writes `runs/kv-sweep-qwen3.8.json` and `runs/kv-sweep-qwen3.8.csv`, and the chart command printed at the end uses that JSON path.

Compare the two runtime columns yourself. The calculator's `q8_0` column is the formula at 1 byte per value. Some runtimes also store a small scale beside each block, so a live number can sit a little above that column.

## 4. Whiteboard

`whiteboard/kv-cache.excalidraw` is the hand-drawn scene: a memory bar (weights, then a KV cache that can grow), a grid of keys and values by layer and token, and the formula, including the 4 GiB to 1 GiB grouped-query step. The weights label sits on a solid white plate so it stays readable on the hatched fill. Open it in [Excalidraw](https://excalidraw.com). Strokes are black on white.

## 5. Render the chart

The chart reads the measurement JSON: predicted cache against measured runtime memory, by context length. It is 1920x1080 at 24 fps. The bottom 150 px is left empty for captions. The y-axis uses round GiB ticks. The last bar and its label finish, then the frame holds for at least 2 seconds. A sample file is built in, so the chart renders before you have a live run. The sample's measured series is the prediction plus a fixed 5 GiB, standing in for weights and compute buffers. That stand-in is not a measurement.

```bash
cd chart
npm install
npx remotion browser ensure
npm run render
```

The file is `chart/out/kv-cache.mp4`. A single frame, useful while you are lining up the shot:

```bash
npm run still
```

After a live sweep, from `chart/`:

```bash
npm run render -- --props=../runs/kv-sweep.json
```

`npm run studio` opens the Remotion studio if you want to scrub the timeline.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

The tests check the 4 GiB example, the 8-KV-head case, the quantized widths, the Qwen shape, and the GGUF and `config.json` readers. They do not start Ollama and they do not download a model.
