#!/usr/bin/env python3
"""Analyze probe JSONL, asserting reset, cold-miss and cache-accounting evidence."""
import argparse,json,re,statistics,math
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('engine',choices=['vllm','sglang','ollama']);ap.add_argument('input');ap.add_argument('--require-primer',action='store_true');a=ap.parse_args()
rows=[json.loads(s) for s in Path(a.input).read_text().splitlines() if s.startswith('{')]
resets={(r['prefix_tokens'],r['rep']):r for r in rows if r['type']=='reset'}
primers={(r['prefix_tokens'],r['rep']):r for r in rows if r['type']=='primer'}
def counter(m,k):
    matches=re.findall(r'^vllm:'+k+r'\{[^\n]*\} ([0-9.e+]+)$',m['body'],re.M)
    assert matches,'Missing counter '+k
    return sum(map(float,matches))
out=[]
for n in [256,1024,4096]:
    pairs=[r for r in rows if r['type']=='pair' and r['prefix_tokens']==n]
    assert len(pairs)==3,('Expected 3 pairs',n,len(pairs))
    cold=[];warm=[];details=[]
    for r in pairs:
        key=n,r['rep'];assert resets[key]['ok_transport']
        if a.require_primer:assert key in primers,'No unrelated same-shape primer recorded'
        if a.engine=='vllm':
            b,m,z=(r[k] for k in ['metrics_before','metrics_between','metrics_after'])
            ch=counter(m,'prefix_cache_hits_total')-counter(b,'prefix_cache_hits_total')
            wh=counter(z,'prefix_cache_hits_total')-counter(m,'prefix_cache_hits_total')
            cq=counter(m,'prefix_cache_queries_total')-counter(b,'prefix_cache_queries_total')
            wq=counter(z,'prefix_cache_queries_total')-counter(m,'prefix_cache_queries_total')
        elif a.engine=='sglang':
            x=r['cold']['events'][-1]['data']['meta_info'];y=r['warm']['events'][-1]['data']['meta_info']
            ch,wh=x['cached_tokens'],y['cached_tokens'];cq,wq=x['prompt_tokens'],y['prompt_tokens']
        else:
            x=r['cold']['events'][-1]['data'];y=r['warm']['events'][-1]['data']
            ch,wh=x['prompt_eval_cached_count'],y['prompt_eval_cached_count']
            cq=x['prompt_eval_count'];wq=n+7
            assert y['prompt_eval_count']==wq or y['prompt_eval_count']+wh==wq,'Unverified prompt-count accounting'
            ps=json.loads(resets[key]['evidence']['ps_after_load']['body'])['models']
            assert len(ps)==1 and ps[0]['context_length']==8192,'Loaded context not matched'
        assert ch==0 and cq==n+7 and wq==n+7,'Cold reset or tokenizer count invalid'
        assert 0<=wh<=wq
        assert r['cold']['ttft_s'] is not None and r['warm']['ttft_s'] is not None
        cold.append(r['cold']['ttft_s']);warm.append(r['warm']['ttft_s'])
        details.append({'rep':r['rep'],'cold_hits':ch,'repeated_hits':wh,'query_tokens':wq,'cold_ttft_s':cold[-1],'repeated_ttft_s':warm[-1]})
    hits=sum(d['repeated_hits'] for d in details);queries=sum(d['query_tokens'] for d in details)
    out.append({'engine':a.engine,'prefix_tokens':n,'pairs':len(pairs),'reset_and_cold_miss_asserted':True,'repeated_token_hit_fraction':hits/queries,'positive_reuse_demonstrated':hits>0,'cold_ttft_p50_s':statistics.median(cold),'repeated_ttft_p50_s':statistics.median(warm),'cold_nearest_rank_p95_s':max(cold),'repeated_nearest_rank_p95_s':max(warm),'ratio_of_median_cold_to_repeated':statistics.median(cold)/statistics.median(warm),'details':details})
print(json.dumps(out,indent=2))
