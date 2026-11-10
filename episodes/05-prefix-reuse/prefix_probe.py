#!/usr/bin/env python3
"""Isolated, raw-text prefix reuse probe; stdlib HTTP, local tokenizer only.
Outputs JSONL evidence. Engine must be isolated and exclusively owned by this test.
"""
import argparse,json,time,urllib.request,urllib.error
from transformers import AutoTokenizer
ap=argparse.ArgumentParser(); ap.add_argument('--engine',choices=['vllm','sglang','ollama'],required=True); ap.add_argument('--port',type=int,required=True); ap.add_argument('--model',default='prefix-local'); ap.add_argument('--repeats',type=int,default=3); ap.add_argument('--prime-after-load',action='store_true'); a=ap.parse_args()
base='http://127.0.0.1:'+str(a.port)
def emit(x): print(json.dumps(x),flush=True)
def call(path,data=None,method=None):
    req=urllib.request.Request(base+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'},method=method)
    try:
        with urllib.request.urlopen(req,timeout=600) as r:
            raw=r.read().decode(); return {'status':r.status,'body':raw}
    except urllib.error.HTTPError as e:
        return {'status':e.code,'body':e.read().decode()}
def metrics():
    if a.engine=='ollama':return {}
    try:return call('/metrics')
    except Exception as e:return {'error':str(e)}
def reset():
    if a.engine=='vllm':
        r=call('/reset_prefix_cache',{},'POST')
        body=r['body'].strip().lower(); ok=r['status']==200 and body not in ('false','{"success":false}')
        try:
            j=json.loads(body)
            if isinstance(j,dict) and j.get('success') is False:ok=False
        except Exception:pass
        return r,ok
    if a.engine=='sglang':
        attempts=[]
        for attempt in range(7):
            r=call('/flush_cache',None,'GET'); attempts.append(r); body=r['body'].strip().lower()
            if r['status']==200 and 'false' not in body:return {'attempts':attempts},True
            if r['status']!=400:break
            time.sleep(5)
        return {'attempts':attempts},False
    r=call('/api/generate',{'model':a.model,'keep_alive':0,'stream':False}); j=json.loads(r['body']); ps=call('/api/ps')
    ok=j.get('done_reason')=='unload' and len(json.loads(ps['body']).get('models',[]))==0
    load=call('/api/generate',{'model':a.model,'keep_alive':'10m','stream':False,'options':{'num_ctx':8192,'num_batch':2048}})
    loaded=call('/api/ps')
    return {'unload':r,'ps_after_unload':ps,'load':load,'ps_after_load':loaded},ok

def run(prompt):
    mem={}
    with open('/proc/meminfo') as mf:
        for line in mf:
            k,v=line.split(':',1);mem[k]=int(v.strip().split()[0])
    if 1-mem['MemAvailable']/mem['MemTotal']>=.85:raise RuntimeError('85% host watermark: no new inference work')
    if a.engine=='vllm':
        path='/v1/completions'; data={'model':a.model,'prompt':prompt,'max_tokens':16,'temperature':0,'seed':0,'stream':True,'stream_options':{'include_usage':True}}
    elif a.engine=='sglang':
        path='/generate'; data={'text':prompt,'sampling_params':{'max_new_tokens':16,'temperature':0,'skip_special_tokens':True},'stream':True}
    else:
        path='/api/generate'; data={'model':a.model,'prompt':prompt,'raw':True,'stream':True,'keep_alive':'10m','options':{'num_ctx':8192,'num_batch':2048,'num_predict':16,'temperature':0,'seed':0}}
    start=time.perf_counter(); first=None; events=[]
    req=urllib.request.Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=600) as r:
        for raw in r:
            line=raw.decode().strip()
            if not line:continue
            if line.startswith('data:'):line=line[5:].strip()
            if line=='[DONE]':continue
            try:j=json.loads(line)
            except Exception:continue
            elapsed=time.perf_counter()-start;events.append({'t':elapsed,'data':j})
            if a.engine=='vllm':content=''.join(c.get('text','') for c in j.get('choices',[]))
            elif a.engine=='sglang':content=j.get('text','')
            else:content=j.get('response','')
            if first is None and content:first=elapsed
    return {'ttft_s':first,'wall_s':time.perf_counter()-start,'events':events}

tok=AutoTokenizer.from_pretrained('/models',local_files_only=True,trust_remote_code=False)
for n in [256,1024,4096]:
    ids=tok.encode(' alpha'* (n*2),add_special_tokens=False)[:n];prefix=tok.decode(ids)
    assert len(tok.encode(prefix,add_special_tokens=False))==n
    for rep in range(a.repeats):
        try:
            reset_evidence,ok=reset(); emit({'type':'reset','engine':a.engine,'prefix_tokens':n,'rep':rep,'ok_transport':ok,'evidence':reset_evidence})
            if not ok:raise RuntimeError('reset transport/body rejected; no cold/warm comparison')
            if a.prime_after_load:
                assert a.engine=='ollama'
                primer=tok.decode(tok.encode('ZEBRA '*(n*2),add_special_tokens=False)[:n])+'\nQuestion P: Reply OK.'
                assert len(tok.encode(primer,add_special_tokens=False))==n+7
                assert tok.encode(primer,add_special_tokens=False)[0]!=tok.encode(prefix,add_special_tokens=False)[0]
                primed=run(primer)
                emit({'type':'primer','engine':a.engine,'prefix_tokens':n,'rep':rep,'prompt':primer,'result':primed})
            before=metrics()
            cold=run(prefix+'\nQuestion A: Reply OK.')
            between=metrics()
            warm=run(prefix+'\nQuestion B: Reply OK.')
            after=metrics()
            emit({'type':'pair','engine':a.engine,'prefix_tokens':n,'rep':rep,'cold':cold,'warm':warm,'metrics_before':before,'metrics_between':between,'metrics_after':after,'prompt_cold':prefix+'\nQuestion A: Reply OK.','prompt_warm':prefix+'\nQuestion B: Reply OK.'})
        except Exception as e:
            emit({'type':'error','engine':a.engine,'prefix_tokens':n,'rep':rep,'error':repr(e)});raise
