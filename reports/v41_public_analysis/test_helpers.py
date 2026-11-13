"""Checks for the analysis helpers (no model, no data files):

    python reports/v41_public_analysis/test_helpers.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ablate as A  # noqa: E402
import doc_codes as D  # noqa: E402
import filter_effect as F  # noqa: E402
import linestop_frames as LS  # noqa: E402
import perturb as P  # noqa: E402
import read_errors as R  # noqa: E402
import train_shapes as T  # noqa: E402

t = "Bir qeyd var; v7.2.92 ilə. Logda IPv6 2001:db8::13b2 qeyd olunub. Son."
s = t.index("2001")
e = s + len("2001:db8::13b2")
g = {"label": "IPV6_ADDRESS", "start": s, "end": e}

# frame, folded frame
assert R.frame(t, s, e) == "Logda IPv6 X qeyd olunub", R.frame(t, s, e)
assert R.norm_frame("Server IPv6-si X yazılıb") == R.norm_frame("Server IPv6-si X yazilib")
t2 = "Məndə IPv6 ünvanı 2001:db8::e6c0-dir. Köhnə"
s2 = t2.index("2001")
assert R.frame(t2, s2, s2 + 14) == "IPv6 ünvanı X-dir", R.frame(t2, s2, s2 + 14)

# split marking and cut characters
p = [{"label": "IPV6_ADDRESS", "start": s, "end": s + 4}]
assert R.marked(t, g, p) == "[2001]:db8::13b2"
assert R.cut_chars(t, g, p) == ":"
assert R.cut_chars(t, g, []) == "2"  # a full miss: cut at the first character
p2 = p + [{"label": "IPV6_ADDRESS", "start": s + 4, "end": e}]
assert R.marked(t, g, p2) == "[2001][:db8::13b2]" and R.cut_chars(t, g, p2) == "1|:"

# shapes
assert R.ipv6_shape("2001:db8::13b2")[:2] == [":: middle", "lower"] and "prefix 2001:db8" in R.ipv6_shape("2001:db8::13b2")
assert R.ipv4_shape("8.8.4.4")[1] == "4 one-digit octets"
assert R.email_shape("bench.user12@synthetic-mail3.invalid")[0] == "local: dot+digit"

# contexts: long "; "-joined benchmark sentences are prose, `a;b;c` rows are tables
assert R.context(t, s, e) == "prose"
row = "e_poçt;kart\nbench.u1@x.invalid;5294;899\n"
assert R.context(row, row.index("bench"), row.index(";5294")) == "CSV / table"
js = '{\n  "ipv6": "2001:db8::1",\n}'
assert R.context(js, js.index("2001"), js.index("2001") + 11) == "JSON"

# sentence splitting (perturb) and sentence spans (ablate)
sent, off = P.sentence(t, s, e)
assert sent == "Logda IPv6 2001:db8::13b2 qeyd olunub." and sent[off:off + 14] == "2001:db8::13b2"
spans = A.sentences(t)
assert [t[a:b].strip() for a, b in spans] == ["Bir qeyd var;", "v7.2.92 ilə.", "Logda IPv6 2001:db8::13b2 qeyd olunub.", "Son."]

# regex shapes: an hh:mm:ss stamp is not IPv6-like; ::ffff: and one-digit IPv4 are caught
R6 = T.SHAPES_RE["IPv6-like (:: or 3+ colons)"]
assert not R6.search("14:05:22") and R6.fullmatch("2001:db8::1") and R6.fullmatch("::1")
assert T.SHAPES_RE["::ffff: + IPv4"].fullmatch("::ffff:10.0.0.1")
assert T.SHAPES_RE["dotted 3 parts (99.99.99)"].search("bənd 9.9.9 ilə") and not T.SHAPES_RE["dotted 3 parts (99.99.99)"].search("10.0.0.1")
assert T.SHAPES_RE["hh:mm, hour > 23 or minute > 59"].fullmatch("27:49") and not T.SHAPES_RE["hh:mm, hour > 23 or minute > 59"].fullmatch("23:59")
assert T.source({"_source": "targeted", "id": "x"}) == "targeted"
assert T.source({"_source": "llm", "_old": True, "id": "x"}) == "old corpus"
assert T.source({"_source": "llm", "id": "sprint1_llm_b6.clean__llm_az_1"}) == "LLM b6"
# doc_codes: a dotted 3-part number (with or without `v`), not an IPv4; an hh:mm time, not hh:mm:ss
DOT, SIXTEEN, _, HHMM = D.CODES.values()
assert DOT.search("bənd 9.9.9 ilə") and DOT.search("versiya v7.2.92") and not DOT.search("10.0.0.1")
assert SIXTEEN.search("kod 1234567812345678") and not SIXTEEN.search("12345678123456789")
assert HHMM.search("saat 14:30") and not HHMM.search("12:34:56")

# filter_effect: why validity-2 drops a span, and what the span was
assert F.reason("TIME", "24:51") == "impossible TIME" and F.reason("TIME", "23:59") == "kept"
assert F.reason("DATE", "30.02.2027") == "impossible DATE" and F.reason("DATE", "28.02.2027") == "kept"
assert F.reason("CARD_SECURITY_CODE", "18275") == "CVV not 3-4 digits" and F.reason("CARD_SECURITY_CODE", "123") == "kept"
assert F.reason("IPV4_ADDRESS", "1.2.3.4") == "D-2 dummy" and F.reason("IPV4_ADDRESS", "256.1.1.1") == "kept"
doc = {"gold": [{"label": "TIME", "start": 0, "end": 5}],
       "decoys": [{"start": 10, "end": 15, "resembles": "TIME", "kind": "time_bad_hour", "policy": False}]}
assert F.kind(doc, {"label": "TIME", "start": 0, "end": 5}) == "real value"
assert F.kind(doc, {"label": "TIME", "start": 10, "end": 15}) == "look-alike: time_bad_hour"
assert F.kind(doc, {"label": "DATE", "start": 10, "end": 15}) == "other false alarm"
assert LS.found([{"label": "EMAIL", "start": 2, "end": 9}], 2, 9, "EMAIL") and not LS.found([], 2, 9, "EMAIL")
# unfiltered_m: the filter is off in this process only, and the cache key changes with it
U = F.U
U.unfiltered()
spans = [{"label": "TIME", "start": 0, "end": 5}]
assert U.predict._drop_impossible_values(spans, "24:51") == spans and F.REAL_FILTER(spans, "24:51") == []
assert U.predict.DECODER_VERSION == "validity-2-filter-off"
print("test_helpers: all checks passed")
