# 06 · Prefix caching: the biggest agent win

> **Lab book:** Local labs → **L6** · Fireworks labs → **F2**  **Watch:** video 11 `11-prefix-caching.mp4`
> **Time:** 30 min  **Cost:** free locally · about $0.03 on Fireworks

## What and why

An agent sends the *same* 3,000-token preamble (instructions, tool definitions, policy)
on every call and changes only the last line. Without a prefix cache the server
re-reads that preamble every time. With one, it keeps the KV cache from last time and
reads only the new part.

It works like a bookmark: if the first 3,000 words are identical, start reading at
word 3,001. It only works if the text is *identical from the very first token*.
Put a timestamp at the top and every call looks new.

```
stable-first    [■■■■■■■■■■ preamble (cached) ■■■■■■■■■■][question]   → TTFT ~20× lower
variable-first  [time+question][■■■■■■■ preamble ■■■■■■■]              → nothing reusable
```

| where | name | what it saves |
|---|---|---|
| vLLM | automatic prefix caching (block hashes) | TTFT, GPU time |
| SGLang | RadixAttention (a tree of shared prefixes) | TTFT, very good for branching agents |
| llama.cpp | slot cache reuse | TTFT |
| Fireworks | prompt caching, on by default, with session affinity via `user` | TTFT **and** the bill: cached input is heavily discounted |

## Read the code first

- `prefix_bench.py → messages()` puts the good pattern and the anti-pattern side by side.
- `extra = {"user": ...}` shows session affinity: the same user stays on the same replica, and so the same cache.
- `felab/mock_server.py → uncached_tokens()` is a 15-line model of block-hash prefix caching.

## Run

```bash
cd lessons/06-prefix-caching
python prefix_bench.py --target mock
python prefix_bench.py --target mock --order variable-first

bash ../02-three-local-servers/serve_llamacpp.sh      # other terminal
python prefix_bench.py --target llamacpp
python prefix_bench.py --target llamacpp --order variable-first

bash mlx_prompt_cache.sh                              # the MLX by-hand version

python prefix_bench.py --target fireworks --usage     # F2: cached_tokens in the usage block
```

## What you should see

```
order           first_ms  rest_p50_ms  speedup_x
stable-first       740.0         36.0       20.3
variable-first     744.0        712.0        1.0   ← one changed token at the top kills it
```

With `--usage` on Fireworks, `cached_tokens` should cover most of `prompt_tokens`.

## Check yourself

1. The customer's agent puts `Current time: …` at the top of the system prompt. What do you tell them? *(Move it to the end. Stable content first, variable content last.)*
2. Why does `user` / session affinity matter on a multi-replica deployment? *(Each replica holds its own cache, so a request routed to a different replica starts cold.)*
3. What is the business case? *(For an agent that is 90% repeated context, most of the input bill becomes cached-token pricing, and TTFT drops by an order of magnitude.)*

## Explain what you learned

> "Their system prompt is identical on every call, so most of the input bill is
> cacheable. Stable first, variable last, session affinity on, and I'll show the
> cached-token count in the usage block."

**Next →** [07 · Structured output](../07-structured-output/)
