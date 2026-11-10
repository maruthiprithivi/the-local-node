"""Reference: how the trimmed prompt was passed to Qwen Code in the run (excerpt of the harness adapter used).
The base Qwen Code command was:
    qwen --approval-mode yolo --auth-type openai --model <model-id> "<task prompt>"
with env QWEN_STREAM_MAX_LIFETIME_MS=0 and ~/.qwen/settings.json rendered from config/qwen-settings.json.tmpl
(managed auto-memory and auto-dream turned off). For the p60 / p30 / pmin levels the adapter inserts
--system-prompt <file text> just before the task prompt; p100 is the stock command with no flag."""
import pathlib


class QwenTrim(QwenCode):  # QwenCode = the base Qwen Code adapter of the (unpublished) benchmark harness
    def __init__(self, name="qwen-trim", options=None, **kw):
        super().__init__(name=name, options=options, **kw)

    def argv(self, ctx):
        a = super().argv(ctx)
        f = self.options.get("system_prompt_file")
        if f:
            a = a[:-1] + ["--system-prompt", pathlib.Path(f).read_text()] + a[-1:]
        return a
