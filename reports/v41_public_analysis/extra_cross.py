"""v4.1 analysis, training-data count: D-51h identical-sentence frames (IPV4_BOTH, ZIP_RIGHT) in targeted training.

    python reports/v41_public_analysis/extra_cross.py v3=<train.docs.jsonl> v4=<train.docs.jsonl>

Counts and shapes only; the example column of extra_bench prints 40 characters around a hit
with digits masked, from our own synthetic training data.
"""
import json,re,sys,collections
FR={'Sorğu qeydində IP ünvanı X kimi yazılıb':r'Sorğu qeydində IP ünvanı (\S+) kimi yazılıb','Formanın IP sahəsində X göstərilib':r'Formanın IP sahəsində (\S+) göstərilib',
    'Jurnalda mənbə IP ünvanı olaraq X qeyd olunub':r'Jurnalda mənbə IP ünvanı olaraq (\S+) qeyd olunub','Hesabatda serverin IP ünvanı X kimi əks olunub':r'Hesabatda serverin IP ünvanı (\S+) kimi əks olunub',
    'ZIP_RIGHT: indeks kimi/olaraq X (tail?)':r'(?:indeks kimi|indeks olaraq|poçt indeksi kimi|indeks sahəsində) (\S+)( məhsul kodu| anbar kodu| \w+ kodu)?'}
for name,path in [a.split('=',1) for a in sys.argv[1:]]:
    c=collections.Counter()
    for line in open(path,encoding='utf-8'):
        d=json.loads(line)
        if d.get('_source')!='targeted': continue
        t=d['text']
        for k,rx in FR.items():
            for m in re.finditer(rx,t):
                s,e=m.span(1)
                lab=next((x['label'] for x in d['entities'] if x['start']<e and x['end']>s),None)
                dec=next((x.get('kind') for x in (d.get('_decoys') or []) if x['start']<e and x['end']>s),None)
                tail=' +tail' if (m.lastindex or 0)>=2 and m.group(2) else ''
                c[(k,('labelled '+lab) if lab else ('look-alike '+dec) if dec else 'unlabelled', tail)]+=1
    print('=====',name)
    for k,v in sorted(c.items()): print(v,k)
