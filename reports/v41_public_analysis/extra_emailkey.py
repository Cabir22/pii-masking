"""v4.1 analysis, training-data count: e_poçt key rows (table/JSON/log) and the | Sahə | Dəyər | header in training.

    python reports/v41_public_analysis/extra_emailkey.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,re,sys,collections
sys.path.insert(0,'reports/v41_public_analysis')
from train_shapes import source
RX=re.compile(r'(?i)(?:\|\s*e[_-]?po[çc]t\s*\|\s*|"e[_-]?po[çc]t"\s*:\s*"|\be[_-]?po[çc]t=|\be[_-]?po[çc]t\s+məlumatı\s+)(\S+?)(?=\s*\||"|\s|$)')
HDR=re.compile(r'\|\s*Sahə\s*\|\s*Dəyər\s*\|')
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter()
    for line in open(path,encoding='utf-8'):
        d=json.loads(line); t=d['text']; src=source(d); src='LLM' if src.startswith('LLM') else src
        c[('docs with | Sahə | Dəyər | header',src)]+=bool(HDR.search(t))
        for m in RX.finditer(t):
            s,e=m.span(1)
            lab=next((x['label'] for x in d['entities'] if x['start']<e and x['end']>s),None)
            dec=next((x.get('kind') for x in (d.get('_decoys') or []) if x['start']<e and x['end']>s),None)
            c[('e_poçt key value: '+('labelled '+lab if lab else 'look-alike '+dec if dec else 'unlabelled'),src)]+=1
    print('=====',name)
    for k,v in sorted(c.items()): print(v,k)
