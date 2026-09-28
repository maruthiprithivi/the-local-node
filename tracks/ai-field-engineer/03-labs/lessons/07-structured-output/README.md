# 07 · Structured output that doesn't break

> **Lab book:** Fireworks labs → **F3**  **Watch:** video 8 `08-platform.mp4` (integration section)
> **Time:** 30 min  **Cost:** free locally · about $0.02 on Fireworks

## What and why

Enterprise code parses the model's reply. If the reply isn't valid JSON, the pipeline
throws. **Constrained decoding** fixes this at the source: at every step the server
masks out tokens that would break the grammar or schema, so the model *cannot* produce
invalid output. Think of a form with dropdowns instead of free-text boxes.

| mode | guarantee | typical validity |
|---|---|---|
| prompt only ("reply with JSON") | none | 85–98% |
| `response_format: json_object` | valid JSON, any keys | ~100% parse, keys can still be wrong |
| `response_format: json_schema` | valid JSON **matching your schema** | ~100% |

Validity is not correctness. A perfectly formatted wrong answer is still wrong, and
that is the job of the eval harness in lesson 09 and the fine-tune in lessons 10 and 11.

## Read the code first

- `data/triage_schema.json` is the contract: an enum category, an integer severity from 1 to 5, and a short string.
- `felab/tickets.py → parse()` is deliberately strict. Leniency would hide real integration failures.
- `structured_output.py → request_kwargs()` holds the three modes. It is one dict each.

## Run

```bash
python data/make_tickets.py                      # once — builds data/tickets/*.jsonl
cd lessons/07-structured-output
python structured_output.py --target mock
python structured_output.py --target llamacpp    # llama.cpp turns json_schema into a grammar
python structured_output.py --target fireworks
```

## What you should see (mock)

```
mode         n   parses_%  schema_valid_%  category_acc_%  p95_ms
prompt       50      86.0            86.0            64.0   535.8
json_object  50     100.0           100.0            78.0   446.7
json_schema  50     100.0           100.0            78.0   446.6
```

## Check yourself

1. Validity is 100% but accuracy is 78%. What next? *(Improve the prompt or add few-shot examples, then fine-tune. Constrained decoding has done its part.)*
2. Why keep the schema in the prompt when `json_schema` already enforces it? *(The model writes better content when it knows the shape. Enforcement alone can force awkward completions.)*
3. What do you do with a reasoning model? *(Put the schema in the prompt, let it reason freely, and validate afterwards.)*

## Explain what you learned

> "Schema-constrained decoding for the format, then a validity and accuracy rate on 50
> of their real tickets. The first is solved by the platform, the second by the model."

**Next →** [08 · Batch API](../08-batch-api/)
