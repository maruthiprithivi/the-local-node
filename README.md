# The Local Node

Open, practical learning materials for people who build and explain technology. Follow a topic from its first working example through measurement, tradeoffs, and a project you can show.

## Learn

| Track | Start learning | Explore the source |
| --- | --- | --- |
| AI Field Engineer | [12-day guided course](https://thelocalnode.dev/ai-field-engineer/) | [Course sequence and runnable code](tracks/ai-field-engineer/COURSE.md) |

The AI Field Engineer track starts with one model reply, then covers serving, benchmarking, evaluation, tuning, and customer recommendations. You can use the free local exercises before choosing any paid cloud labs.

## Follow along

Use the [course-to-code index](tracks/ai-field-engineer/COURSE.md) to follow the same sequence as the website. Every lab README links back to its lesson; website code sections link to the corresponding GitHub folder and file. The index is generated from the website course model so the order stays aligned.

The [playbook](PLAYBOOK.md) is the standard way to reproduce an episode demo end to end.

See [contributing](CONTRIBUTING.md) for lesson updates, alignment checks and the pre-push secret scan. Keep real credentials and private material out of this public repository; use your own environment values with the placeholder `.env.example`.

## In this repository

- [`tracks/`](tracks/) contains the learning materials, with one directory per topic.
- [`PLAYBOOK.md`](PLAYBOOK.md) is how to reproduce an episode demo on the reference machines.
- [`episodes/01-kv-cache/`](episodes/01-kv-cache/) is the follow-along kit for episode one. It sizes a model's KV cache, measures that cache on Ollama, and renders the chart.
- [`episodes/02-super-agent/`](episodes/02-super-agent/) is the reproduction kit for comparing DeepSeek's Super-agent prototype with a single agent session on the same five bug fixes.
- [`episodes/03-lfm3-tool-loop/`](episodes/03-lfm3-tool-loop/) is the reproduction kit for testing how many chained tool calls LiquidAI LFM3-1.7B gets right with ~3K-token tool results, plus its decode-speed numbers.
- [`episodes/04-prompt-trim/`](episodes/04-prompt-trim/) is the reproduction kit for trimming Qwen Code's system prompt on a local Qwen3.8-27B: the prompt levels, settings, analysis scripts and results.
- [`episodes/05-prefix-reuse/`](episodes/05-prefix-reuse/) is the reproduction kit for a raw-text prefix-reuse timing and cache microbenchmark on vLLM, SGLang and Ollama.
- [`website/`](website/) contains the code that publishes the guided courses.
- [`assets/brand/`](assets/brand/) contains shared artwork for The Local Node.

Have a correction or a clearer example? Open an issue or edit the relevant lesson and send a pull request. Each track's README tells you where to start.
