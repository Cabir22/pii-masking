"""v4.1 analysis, training-data count: benchmark frames (Logda/Server/IPv6 ünvanı …) in training: labelled, look-alike or unlabelled value.

    python reports/v41_public_analysis/extra_frames.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,re,sys,collections
sys.path.insert(0,'reports/v41_public_analysis')
from train_shapes import source
FR=[("Logda IPv4 X qeyd olunub",r"Logda IPv4 (\S+) qeyd olun"),("Logda IPv6 X qeyd olunub",r"Logda IPv6 (\S+) qeyd olun"),
    ("Server IPv6-si X yazılıb",r"Server IPv6-si (\S+) yazıl"),("Server ünvanı X yazılıb",r"Server ünvanı (\S+) yazıl"),
    ("IPv6 ünvanı X kimi",r"IPv6 ünvanı (\S+) kimi"),("Mənbə IP X kimi",r"Mənbə IP (\S+) kimi"),
    ("Şəbəkə tarixçəsində X görünür",r"Şəbəkə tarixçəsində (\S+) görünür"),("IP X görünür (any)",r"\bIP(?:v[46])? (\S+) görünür"),
    ("Logda IPv[46] (any)",r"Logda IP\S* (\S+)"),("Server IPv[46]-s[iı] (any)",r"Server IPv[46]-s\S* (\S+)")]
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter()
    for line in open(path,encoding='utf-8'):
        d=json.loads(line); t=d['text']; src=source(d); src='LLM' if src.startswith('LLM') else src
        for fn,rx in FR:
            for m in re.finditer(rx,t):
                s,e=m.span(1)
                lab=next((x['label'] for x in d['entities'] if x['start']<e and x['end']>s),None)
                dec=next((x.get('kind') for x in (d.get('_decoys') or []) if x['start']<e and x['end']>s),None)
                st=('labelled '+lab) if lab else ('look-alike '+dec) if dec else 'unlabelled'
                c[(fn,st,src)]+=1
    print('=====',name)
    for k,v in sorted(c.items()): print(v,k)
