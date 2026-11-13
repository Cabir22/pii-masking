"""v4.1 analysis, training-data count: email local-part/domain shapes (user…, word.wordDIGITS, .invalid) in training.

    python reports/v41_public_analysis/extra_emailuser.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,re,sys,collections
sys.path.insert(0,'reports/v41_public_analysis')
from train_shapes import source
RX=re.compile(r'[\w.+-]*@[\w.-]*')
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter()
    for line in open(path,encoding='utf-8'):
        d=json.loads(line); t=d['text']; src=source(d); src='LLM' if src.startswith('LLM') else src
        for m in RX.finditer(t):
            v=m.group(); s,e=m.span()
            lab=next((x['label'] for x in d['entities'] if x['start']<e and x['end']>s),None)
            dec=next((x.get('kind') for x in (d.get('_decoys') or []) if x['start']<e and x['end']>s),None)
            st=('labelled' if lab=='EMAIL' else 'look-alike '+dec if dec else 'unlabelled/other')
            loc=v.split('@')[0].lower()
            for f,ok in (('local starts user',loc.startswith('user')),('local has .user',".user" in loc),('local word.wordDIGITS',bool(re.fullmatch(r'[a-z]+\.[a-z]+\d+',loc))),('tld .invalid',v.lower().endswith('.invalid')),('domain has digit',bool(re.search(r'@[^.]*\d',v)))):
                if ok: c[(f,st,src)]+=1
    print('=====',name)
    for k,v in sorted(c.items()): print(v,k)
