"""v4.1 analysis, training-data count: digit tokens before kimi / qeyd olunub / yazılıb / görünür / göstərilib in training.

    python reports/v41_public_analysis/extra_rightctx.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,re,sys,collections
sys.path.insert(0,'reports/v41_public_analysis')
from train_shapes import source
RX=re.compile(r"(?<!\S)(\S*\d\S*?)[,.]?\s+(kimi|qeyd olun\w*|yazıl\w*|görünür|göstəril\w*)\b")
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter()
    for line in open(path,encoding='utf-8'):
        d=json.loads(line); t=d['text']; src=source(d); src='LLM' if src.startswith('LLM') else src
        for m in RX.finditer(t):
            s,e=m.span(1); w=m.group(2)
            w='kimi' if w=='kimi' else 'qeyd olun-' if w.startswith('qeyd') else 'yazıl-' if w.startswith('yaz') else 'görünür' if w=='görünür' else 'göstəril-'
            lab=next((x['label'] for x in d['entities'] if x['start']<e and x['end']>s),None)
            dec=next((x for x in (d.get('_decoys') or []) if x['start']<e and x['end']>s),None)
            st='labelled' if lab else 'look-alike' if dec else 'unlabelled'
            c[(w,st,src)]+=1
            c[(w,st,'all')]+=1
    print('=====',name)
    for w in ['kimi','qeyd olun-','yazıl-','görünür','göstəril-']:
        row=[]
        for src in ['targeted','LLM','old corpus','all']:
            L,A,U=(c[(w,s,src)] for s in ('labelled','look-alike','unlabelled'))
            row.append(f"{src}: lab {L} / look {A} / unl {U}")
        print(w,' | '.join(row))
