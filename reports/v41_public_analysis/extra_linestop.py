"""v4.1 analysis, training-data count: how the sentence or line holding a labelled IPv4/IPv6 ends ('.', ';', other punctuation, nothing), by source.

    python reports/v41_public_analysis/extra_linestop.py v4=<train.docs.jsonl> v4.1=<train.docs.jsonl>
"""
import collections
import json
import re
import sys

sys.path.insert(0, 'reports/v41_public_analysis')
from train_shapes import source  # noqa: E402

END = re.compile(r"[.;!?](?=\s|$)|\n|$")
for name, path in [a.split('=', 1) for a in sys.argv[1:]]:
    c = collections.Counter()
    for line in open(path, encoding='utf-8'):
        d = json.loads(line)
        t = d['text']
        for s in d.get('entities', []):
            if s['label'] not in ('IPV4_ADDRESS', 'IPV6_ADDRESS'):
                continue
            m = END.search(t, s['end'])
            end = t[m.start():m.end()] if m else ''
            kind = {'.': "'.'", ';': "';'", '\n': 'line break', '': 'end of text'}.get(end, 'other (! ?)')
            c[(s['label'], source(d), kind)] += 1
    print('=====', name)
    for k, n in sorted(c.items()):
        print(n, k)
