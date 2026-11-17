"""Parse every transcript format into one normalized session record.

Normalized session:
  {
    "steps": [ {"i", "tool", "kind": "shell"|"edit"|"read"|"other",
                "cmd", "paths", "output", "exit", "exit_src", "tool_error"} ],
    "final": str | None,          # last agent message shown to the user
    "compactions": int,
  }
exit_src: "explicit" (exit code printed in the transcript), "inferred0"
(harness prints a code only on failure, none printed), or None (unknown).
"""
from __future__ import annotations

import json
import re

SHELL_TOOLS = {"run_shell_command", "bash", "shell", "exec", "execute", "cmd"}
EDIT_TOOLS = {"edit", "write", "write_file", "replace", "apply_patch", "multi_edit",
              "multiedit", "str_replace", "str_replace_editor", "create_file",
              "patch", "notebook_edit", "hashline_edit", "ast_edit"}
READ_TOOLS = {"read", "read_file", "read_many_files", "glob", "grep", "ls",
              "list_directory", "search_file_content", "find", "rg"}

EXIT_PATTERNS = [
    re.compile(r"^Exit Code: (-?\d+)", re.M),                 # Qwen Code
    re.compile(r"Command exited with code (-?\d+)"),          # omp, pi
    re.compile(r"\[exit code: (-?\d+)\]"),                    # dsh
    re.compile(r"^exit=(-?\d+)$", re.M),                      # t2 custom agent
]


def _jl(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # harness banner lines such as "[qbench] ..."
    return out


def _text(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "\n".join(_text(p) for p in x)
    if isinstance(x, dict):
        if "text" in x and isinstance(x["text"], str):
            return x["text"]
        if "output" in x:
            return _text(x["output"])
        if "content" in x:
            return _text(x["content"])
        if "error" in x:
            return _text(x["error"])
        return json.dumps(x)[:4000]
    return str(x)


def _exit_from_text(out):
    for p in EXIT_PATTERNS:
        m = p.findall(out or "")
        if m:
            return int(m[-1])
    return None


def _kind(tool):
    t = (tool or "").lower()
    if t in SHELL_TOOLS:
        return "shell"
    if t in EDIT_TOOLS:
        return "edit"
    if t in READ_TOOLS:
        return "read"
    return "other"


def _paths(args):
    if not isinstance(args, dict):
        return []
    ps = []
    for k in ("file_path", "path", "filePath", "absolute_path", "target_file", "file"):
        v = args.get(k)
        if isinstance(v, str):
            ps.append(v)
    for k in ("patch", "input", "patchText"):
        v = args.get(k)
        if isinstance(v, str):
            ps += re.findall(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", v, re.M)
            ps += re.findall(r"^\+\+\+ b/(.+)$", v, re.M)
            ps += re.findall(r"^\[([^\]#\n]+)#[0-9A-Fa-f]+\]", v, re.M)  # omp hashline edits
    edits = args.get("edits")
    if isinstance(edits, list):
        for e in edits:
            if isinstance(e, dict):
                ps += _paths(e)
    return ps


def _cmd(args):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return args
    if isinstance(args, dict):
        for k in ("command", "cmd", "script"):
            if isinstance(args.get(k), str):
                return args[k]
    return ""


def _mkstep(i, tool, args, output, exit_code=None, exit_src=None, tool_error=False):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {"raw": args}
    kind = _kind(tool)
    out = output or ""
    if exit_code is None and kind == "shell":
        e = _exit_from_text(out)
        if e is not None:
            exit_code, exit_src = e, "explicit"
    return {"i": i, "tool": tool, "kind": kind, "cmd": _cmd(args) if kind == "shell" else "",
            "paths": _paths(args), "args": args if kind != "shell" else None,
            "output": out, "exit": exit_code, "exit_src": exit_src, "tool_error": bool(tool_error)}


def _finish(steps, inferred_zero):
    """Harnesses that print an exit code only on failure: a shell step that
    ran to completion with no printed code is recorded as exit 0 (inferred)."""
    if inferred_zero:
        for s in steps:
            if s["kind"] == "shell" and s["exit"] is None and not s["tool_error"]:
                s["exit"], s["exit_src"] = 0, "inferred0"
    for n, s in enumerate(steps):
        s["i"] = n
    return steps


# ---------------------------------------------------------------- formats

def parse_qwen(path):
    recs = _jl(path)
    calls, steps, final, comp = {}, [], None, 0
    for d in recs:
        t = d.get("type")
        if t == "system" and "compress" in str(d.get("subtype", "")):
            comp += 1
        msg = d.get("message") or {}
        if t == "assistant":
            texts, has_call = [], False
            for p in msg.get("parts", []):
                if "functionCall" in p:
                    has_call = True
                    fc = p["functionCall"]
                    st = _mkstep(0, fc.get("name"), fc.get("args") or {}, "")
                    calls[fc.get("id")] = st
                    steps.append(st)
                elif p.get("text") and not p.get("thought"):
                    texts.append(p["text"])
            if texts and not has_call:
                final = "\n".join(texts).strip()
            elif texts and has_call:
                pass
        elif t == "tool_result":
            for p in msg.get("parts", []):
                fr = p.get("functionResponse")
                if not fr:
                    continue
                st = calls.get(fr.get("id"))
                resp = fr.get("response") or {}
                out = _text(resp.get("output")) if "output" in resp else _text(resp)
                err = "error" in resp and resp.get("error")
                if st is None:
                    continue
                st["output"] = out
                st["tool_error"] = bool(err)
                if st["kind"] == "shell":
                    e = _exit_from_text(out)
                    if e is not None:
                        st["exit"], st["exit_src"] = e, "explicit"
    return {"steps": _finish(steps, False), "final": final, "compactions": comp}


def parse_omp(path):
    recs = _jl(path)
    calls, steps, final, comp = {}, [], None, 0
    for d in recs:
        if d.get("type") == "compaction":
            comp += 1
        m = d.get("message") or {}
        role = m.get("role")
        if role == "assistant":
            texts, has_call = [], False
            for p in m.get("content", []):
                if p.get("type") == "toolCall":
                    has_call = True
                    st = _mkstep(0, p.get("name"), p.get("arguments") or {}, "")
                    if p.get("name") == "eval":  # omp's Python runner
                        a = p.get("arguments") or {}
                        st["kind"], st["cmd"] = "shell", "eval: " + str(a.get("code", ""))[:2000]
                    calls[p.get("id")] = st
                    steps.append(st)
                elif p.get("type") == "text" and p.get("text", "").strip():
                    texts.append(p["text"])
            if texts and not has_call:
                final = "\n".join(texts).strip()
        elif role == "toolResult":
            st = calls.get(m.get("toolCallId"))
            if st is None:
                continue
            out = _text(m.get("content"))
            st["output"] = out
            st["tool_error"] = bool(m.get("isError")) and st["kind"] != "shell"
            if st["kind"] == "shell":
                e = _exit_from_text(out)
                if e is not None:
                    st["exit"], st["exit_src"] = e, "explicit"
                elif m.get("isError") and st["tool"] == "eval":
                    st["exit"], st["exit_src"] = 1, "tool-flag"
                elif m.get("isError"):
                    st["tool_error"] = True
    return {"steps": _finish(steps, True), "final": final, "compactions": comp}


def parse_dsh_log(path):
    recs = _jl(path)
    calls, steps, final = {}, [], None
    for d in recs:
        t = d.get("type")
        if t == "tool_call":
            st = _mkstep(0, d.get("tool"), d.get("input") or {}, "")
            calls[d.get("callId")] = st
            steps.append(st)
        elif t == "tool_result":
            st = calls.get(d.get("callId"))
            if st is None:
                continue
            out = _text(d.get("result"))
            st["output"] = out
            st["tool_error"] = d.get("status") == "error"
            if st["kind"] == "shell":
                e = _exit_from_text(out)
                if e is not None:
                    st["exit"], st["exit_src"] = e, "explicit"
        elif t == "final":
            final = (d.get("text") or "").strip()
    return {"steps": _finish(steps, True), "final": final, "compactions": 0}


def parse_dsh_v4(path):
    recs = _jl(path)
    calls, steps, final, comp, settled = {}, [], None, 0, {}
    for d in recs:
        t = d.get("type", "")
        data = d.get("data") or {}
        if "compact" in t:
            comp += 1
        if t == "tool/call":
            st = _mkstep(0, data.get("name"), data.get("arguments") or {}, "")
            calls[data.get("callId")] = st
            steps.append(st)
        elif t == "tool/result":
            msg = data.get("message") or {}
            st = calls.get(msg.get("toolCallId"))
            if st is None:
                continue
            out = _text(msg.get("content"))
            st["output"] = out
            st["tool_error"] = bool(msg.get("isError"))
            if st["kind"] == "shell":
                e = _exit_from_text(out)
                if e is not None:
                    st["exit"], st["exit_src"] = e, "explicit"
        elif t == "job/settled":
            cid = ((data.get("toolCall") or {}).get("callId"))
            m = re.search(r"exit code: (-?\d+)", str(data.get("detail", "")))
            if cid and m:
                settled[cid] = int(m.group(1))
        elif t == "assistant/message":
            msg = data.get("message") or {}
            texts = [p.get("text", "") for p in msg.get("content", [])
                     if p.get("type") == "text" and p.get("text", "").strip()]
            has_call = any(p.get("type") in ("tool_call", "toolCall", "tool-call")
                           for p in msg.get("content", []))
            if texts and not has_call:
                final = "\n".join(texts).strip()
    for cid, st in calls.items():
        if st["kind"] == "shell" and st["exit"] is None and cid in settled:
            st["exit"], st["exit_src"] = settled[cid], "explicit"
    return {"steps": _finish(steps, False), "final": final, "compactions": comp}


def parse_requests(path):
    recs = [r for r in _jl(path) if isinstance(r.get("request"), dict)]
    if not recs:
        return {"steps": [], "final": None, "compactions": 0}
    last = max(recs, key=lambda r: (len(r["request"].get("messages") or []), r.get("seq", 0)))
    msgs = last["request"].get("messages") or []
    calls, steps = {}, []
    for m in msgs:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                st = _mkstep(0, fn.get("name"), fn.get("arguments") or "{}", "")
                calls[tc.get("id")] = st
                steps.append(st)
        elif m.get("role") == "tool":
            st = calls.get(m.get("tool_call_id"))
            if st is None:
                continue
            out = _text(m.get("content"))
            st["output"] = out
            if st["kind"] == "shell":
                e = _exit_from_text(out)
                if e is not None:
                    st["exit"], st["exit_src"] = e, "explicit"
    final = None
    resp = last.get("response") or {}
    if resp.get("content") and not resp.get("tool_calls"):
        final = resp["content"].strip()
    else:
        for r in sorted(recs, key=lambda r: r.get("seq", 0)):
            rs = r.get("response") or {}
            if rs.get("content") and not rs.get("tool_calls"):
                final = rs["content"].strip()
    return {"steps": _finish(steps, True), "final": final, "compactions": 0}


def parse_t2(path):
    d = json.load(open(path))
    steps = []
    for c in d.get("calls", []):
        steps.append(_mkstep(0, "bash", {"command": c.get("cmd", "")}, c.get("out", ""),
                             exit_code=c.get("rc"), exit_src="explicit" if c.get("rc") is not None else None))
    return {"steps": _finish(steps, False), "final": (d.get("final") or "").strip(), "compactions": 0}


def parse_aider(path):
    """Aider benchmark chat history. The agent has no shell: the benchmark
    harness builds and runs the tests and writes the output into the history as
    a plain fenced block (and feeds failures back as a '####' user turn). Each
    plain fenced block that looks like test or build output is recorded as a
    shell step with tool='harness-test'. The final message is the last stretch of
    assistant prose."""
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    testlike = re.compile(r"(passed|failed|FAIL|Error|error:|test result|Tests:|BUILD (SUCCESSFUL|FAILED)|"
                          r"assertions|^ok\s|panicked|Traceback)", re.M)
    events, i, chunk, chunk_start = [], 0, [], None

    def flush():
        nonlocal chunk, chunk_start
        txt = "\n".join(chunk).strip()
        if txt.replace("`", "").strip():
            events.append(("text", chunk_start, txt))
        chunk, chunk_start = [], None

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("####") or ln.startswith(">"):
            flush()
            m = re.search(r"Applied edit to (\S+)", ln)
            if m:
                events.append(("edit", i, m.group(1)))
            i += 1
            continue
        if ln.strip() == "```":  # plain fence: harness output
            j = i + 1
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            body = "\n".join(lines[i + 1:j])
            if testlike.search(body) and "<<<<<<< SEARCH" not in body:
                flush()
                events.append(("test", i, body))
                i = j + 1
                continue
        if chunk_start is None:
            chunk_start = i
        chunk.append(ln)
        if ln.strip().startswith("```") and ln.strip() != "```":  # code fence inside a reply
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                chunk.append(lines[j])
                j += 1
            if j < len(lines):
                chunk.append(lines[j])
            i = j + 1
            continue
        i += 1
    flush()
    # drop the opening chat banner/user task (no assistant text before first '####' block ends)
    texts = [e for e in events if e[0] == "text"]
    final = texts[-1][2] if texts else None
    final_pos = texts[-1][1] if texts else -1
    steps = []
    for kind, pos, val in events:
        if kind == "edit":
            steps.append(_mkstep(0, "edit", {"file_path": val}, "applied"))
        elif kind == "test":
            st = _mkstep(0, "harness-test", {"command": "<benchmark test run" +
                                             (", after final reply>" if pos > final_pos else ">")}, val)
            st["kind"], st["cmd"] = "shell", st["args"]["command"]
            steps.append(st)
    return {"steps": _finish(steps, False), "final": final, "compactions": 0}


PARSERS = {
    "qwen-chat-jsonl": parse_qwen,
    "omp-jsonl": parse_omp,
    "dsh-agent-log": parse_dsh_log,
    "dsh-session-v4": parse_dsh_v4,
    "requests-jsonl": parse_requests,
    "t2-openshell-json": parse_t2,
    "aider-chat-history": parse_aider,
}
