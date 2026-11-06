#!/usr/bin/env python3
"""Host side: TCP 127.0.0.1:<port> -> unix socket relay for the network-less Gitea forge. Logs each connection.
usage: relay.py <port> <unix socket path> <log file>"""
import asyncio, sys, time
PORT = int(sys.argv[1]); SOCK = sys.argv[2]; LOG = sys.argv[3]
def log(m):
    with open(LOG, "a") as f: f.write(f"{time.strftime('%F %T')} {m}\n")
async def pipe(r, w):
    try:
        while (b := await r.read(65536)): w.write(b); await w.drain()
    except Exception: pass
    finally:
        try: w.close()
        except Exception: pass
async def handle(cr, cw):
    peer = cw.get_extra_info("peername")
    try: ur, uw = await asyncio.open_unix_connection(SOCK)
    except Exception as e:
        log(f"conn {peer} unix-fail {e}"); cw.close(); return
    await asyncio.gather(pipe(cr, uw), pipe(ur, cw))
async def main():
    srv = await asyncio.start_server(handle, "127.0.0.1", PORT)
    log(f"relay up 127.0.0.1:{PORT} -> {SOCK}")
    async with srv: await srv.serve_forever()
asyncio.run(main())
