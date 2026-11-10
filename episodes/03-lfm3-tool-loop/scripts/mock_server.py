# Mock OpenAI-compatible server for testing toolloop.py without a GPU.
# Usage: python3 mock_server.py PORT FAIL_AT   (repeats the previous call at tool-call number FAIL_AT to exercise the repeat/loop detector)
import json, re, http.server, sys
FAIL_AT = int(sys.argv[2])
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        last = b["messages"][-1]["content"]; ncalls = sum(1 for m in b["messages"] if m["role"]=="tool")
        mm = re.search(r"NEXT ACTION: call the tool `(\w+)` with arguments (\{.*\})", last)
        msg = {"role":"assistant","content":""}
        if mm and ncalls != FAIL_AT:
            msg["tool_calls"]=[{"id":"c%d"%ncalls,"type":"function","function":{"name":mm.group(1),"arguments":mm.group(2)}}]
        elif mm:
            prev=[m for m in b["messages"] if m["role"]=="assistant"][-1]["tool_calls"][0]
            msg["tool_calls"]=[prev]
        else:
            w = re.search(r"final word: (\S+)", last); msg["content"]= w.group(1) if w else "?"
        r = {"choices":[{"message":msg,"finish_reason":"stop"}],"usage":{"prompt_tokens":len(json.dumps(b))//4,"completion_tokens":5}}
        d=json.dumps(r).encode(); self.send_response(200); self.send_header("Content-Length",str(len(d))); self.end_headers(); self.wfile.write(d)
http.server.HTTPServer(("127.0.0.1",int(sys.argv[1])),H).serve_forever()
