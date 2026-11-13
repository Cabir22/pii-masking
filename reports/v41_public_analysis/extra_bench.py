"""v4.1 analysis, training-data count: the words bench / .invalid / synthetic-mail in training.

    python reports/v41_public_analysis/extra_bench.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,re,sys,collections
sys.path.insert(0,'reports/v41_public_analysis')
from train_shapes import source
RX=re.compile(r"bench|\.invalid\b|synthetic-mail|user\d+@",re.I)
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter(); ex={}
    for line in open(path,encoding='utf-8'):
        d=json.loads(line); t=d['text']; src=source(d)
        for m in RX.finditer(t):
            s,e=m.span()
            lab=next((x['label'] for x in d['entities'] if x['start']<e and x['end']>s),None)
            dec=next((x.get('kind') for x in (d.get('_decoys') or []) if x['start']<e and x['end']>s),None)
            k=(m.group().lower() if not m.group().lower().startswith('user') else 'userNNN@', lab or ('look-alike '+dec if dec else 'unlabelled'), src)
            c[k]+=1
            if k not in ex: ex[k]=re.sub(r'\d','9',t[max(0,s-40):e+40])
    print('=====',name)
    for k,v in sorted(c.items()): print(v,k,'|',repr(ex[k]))
