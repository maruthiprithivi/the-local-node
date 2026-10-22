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
- `nvidia-smi` on `PATH` if you want the GPU column. The script still finishes without it.

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
| `measured_runtime_bytes` | `size` from Ollama's process list, weights included |
| `measured_vram_bytes` | `size_vram` when Ollama reports it, otherwise empty |
| `gpu_memory_bytes` | `nvidia-smi` memory.used, on Linux, when the tool is there |
| `process_rss_bytes` | sum of resident memory for processes named ollama, a fallback |
| `ttft_ms` | wall time to the first token on a second, already-loaded request |
| `load_ms` | time to the first token on the request that loaded the model |

On a Mac the runtime size is the unified-memory figure. There is no separate GPU counter, and the JSON says so. On Linux, a missing `nvidia-smi` leaves `gpu_memory_bytes` empty and the sweep continues. A context the server refuses is one row with a note, not a failed run.

`measured_runtime_bytes` will sit above `predicted_kv_bytes`, because the runtime size includes the weights. Compare the change from one context to the next. Doubling the context doubles the predicted cache. The runtime column should move with it, on top of a size that stays put.

To try a quantized cache, restart Ollama with `OLLAMA_KV_CACHE_TYPE=q8_0` (flash attention has to be on), then run the sweep again to a second file:

```bash
python measure_kv.py --out runs/kv-sweep-q8
```

Compare the two runtime columns yourself. The calculator's `q8_0` column is the formula at 1 byte per value. Some runtimes also store a small scale beside each block, so a live number can sit a little above that column.

## 4. Whiteboard

`whiteboard/kv-cache.excalidraw` is the hand-drawn scene: a memory bar (weights, then a KV cache that can grow), a grid of keys and values by layer and token, and the formula, including the 4 GiB to 1 GiB grouped-query step. Open it in [Excalidraw](https://excalidraw.com). Strokes are black on white.

## 5. Render the chart

The chart reads the measurement JSON: predicted cache against measured runtime memory, by context length. It is 1920x1080 at 24 fps. The bottom 150 px is left empty for captions. A sample file is built in, so the chart renders before you have a live run. The sample's measured series is the prediction plus a fixed 5 GiB. That stand-in is not a measurement.

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
