#!/usr/bin/env python3
"""In-sandbox TCP forwarder: 127.0.0.1:<listen_port> -> <host>:<port> outside the sandbox.

Run it with the dedicated interpreter copy /opt/kit-bin/kit-fwd (see docker/Dockerfile.agent). The sandbox network
policy allows egress ONLY for that binary and ONLY to the model and forge ports on the sandbox's host alias, so
everything else in the sandbox (dsh, git, gh, curl, python3) can reach the model and forge only via 127.0.0.1.

usage: kit-fwd fwd.py <listen_port> tcp:<host>:<port>
"""
import asyncio, sys
LPORT = int(sys.argv[1]); _, RHOST, RPORT = sys.argv[2].split(":"); RPORT = int(RPORT)
async def pipe(r, w):
    try:
        while (b := await r.read(65536)): w.write(b); await w.drain()
    except Exception: pass
    finally:
        try: w.close()
        except Exception: pass
async def handle(cr, cw):
    try: ur, uw = await asyncio.open_connection(RHOST, RPORT)
    except Exception as e:
        print(f"connect {RHOST}:{RPORT} failed: {e}", flush=True); cw.close(); return
    await asyncio.gather(pipe(cr, uw), pipe(ur, cw))
async def main():
    srv = await asyncio.start_server(handle, "127.0.0.1", LPORT)
    print(f"fwd up 127.0.0.1:{LPORT} -> {RHOST}:{RPORT}", flush=True)
    async with srv: await srv.serve_forever()
asyncio.run(main())
