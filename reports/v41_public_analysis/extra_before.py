"""v4.1 analysis, training-data count: the character before EMAIL/IPv4/IPv6 spans in training.

    python reports/v41_public_analysis/extra_before.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,sys,collections
sys.path.insert(0,'reports/v41_public_analysis')
from train_shapes import source
LAB=('EMAIL','IPV6_ADDRESS','IPV4_ADDRESS')
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter()
    for line in open(path,encoding='utf-8'):
        d=json.loads(line); t=d['text']; src=source(d); src='LLM' if src.startswith('LLM') else src
        ents=d['entities']
        for e in ents:
            if e['label'] in LAB:
                ch=t[e['start']-1:e['start']] if e['start'] else '^'
                k={' ':'space','\n':'newline','^':'start'}.get(ch, 'letter/digit' if ch.isalnum() else ch)
                c[(e['label'],'before',k,src)]+=1
                # another label touching right before (no gap) -> two spans glued
        # EMAIL spans that start right after another EMAIL piece or inside a dotted token
        for e in ents:
            if e['label']=='EMAIL':
                lp=t[e['start']:e['end']].split('@')[0]
                if '.' in lp:
                    # same email local part also appearing elsewhere split? count email-like text before span
                    pass
    print('=====',name)
    for k,v in sorted(c.items()):
        if k[2] not in ('space','newline','start') : print(v,k)
