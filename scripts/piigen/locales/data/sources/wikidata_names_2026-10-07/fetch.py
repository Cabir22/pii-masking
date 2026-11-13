"""Fetch the most common given and family names per citizenship from Wikidata."""
import csv
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "wikidata_names_2026-10-07"
OUT.mkdir(exist_ok=True)

# origin -> Wikidata citizenship items
COUNTRIES = {
    "ru": ["Q159"],                       # Russia
    "tr": ["Q43"],                        # Turkey
    "ka": ["Q230"],                       # Georgia
    "fa": ["Q794"],                       # Iran
    "ar": ["Q79", "Q851", "Q796", "Q858", "Q810"],  # Egypt, Saudi Arabia, Iraq, Syria, Jordan
    "en": ["Q145", "Q30"],                # UK, USA
    "de": ["Q183"],                       # Germany
    "fr": ["Q142"],                       # France
}
LANGS = "en,az,ru,tr,ka,de,fr"

GIVEN = """SELECT ?g ?cls ?n ?en ?az ?ru ?tr ?ka ?de ?fr WHERE {
  { SELECT ?g ?cls (COUNT(DISTINCT ?p) AS ?n) WHERE {
      VALUES ?country { %(countries)s }
      ?p wdt:P27 ?country ; wdt:P735 ?g .
      ?g wdt:P31 ?cls . VALUES ?cls { wd:Q12308941 wd:Q11879590 }
    } GROUP BY ?g ?cls ORDER BY DESC(?n) LIMIT %(limit)d }
  OPTIONAL { ?g rdfs:label ?en FILTER(LANG(?en) = "en") }
  OPTIONAL { ?g rdfs:label ?az FILTER(LANG(?az) = "az") }
  OPTIONAL { ?g rdfs:label ?ru FILTER(LANG(?ru) = "ru") }
  OPTIONAL { ?g rdfs:label ?tr FILTER(LANG(?tr) = "tr") }
  OPTIONAL { ?g rdfs:label ?ka FILTER(LANG(?ka) = "ka") }
  OPTIONAL { ?g rdfs:label ?de FILTER(LANG(?de) = "de") }
  OPTIONAL { ?g rdfs:label ?fr FILTER(LANG(?fr) = "fr") }
} ORDER BY DESC(?n)"""

# Family names of men: Russian family names have a feminine form (Petrova),
# which build_foreign_names.py derives from the masculine one.
FAMILY = """SELECT ?f ?n ?en ?az ?ru ?tr ?ka ?de ?fr WHERE {
  { SELECT ?f (COUNT(DISTINCT ?p) AS ?n) WHERE {
      VALUES ?country { %(countries)s }
      ?p wdt:P27 ?country ; wdt:P21 wd:Q6581097 ; wdt:P734 ?f .
    } GROUP BY ?f ORDER BY DESC(?n) LIMIT %(limit)d }
  OPTIONAL { ?f rdfs:label ?en FILTER(LANG(?en) = "en") }
  OPTIONAL { ?f rdfs:label ?az FILTER(LANG(?az) = "az") }
  OPTIONAL { ?f rdfs:label ?ru FILTER(LANG(?ru) = "ru") }
  OPTIONAL { ?f rdfs:label ?tr FILTER(LANG(?tr) = "tr") }
  OPTIONAL { ?f rdfs:label ?ka FILTER(LANG(?ka) = "ka") }
  OPTIONAL { ?f rdfs:label ?de FILTER(LANG(?de) = "de") }
  OPTIONAL { ?f rdfs:label ?fr FILTER(LANG(?fr) = "fr") }
} ORDER BY DESC(?n)"""


def run(query: str, path: Path) -> int:
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": query})
    req = urllib.request.Request(url, headers={
        "User-Agent": "pii-masking-model name pool builder (research)",
        "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read().decode("utf-8")
    path.write_text(data, encoding="utf-8", newline="")
    return len(list(csv.reader(data.splitlines()))) - 1


# Countries with too many people for the server's 60 s limit: count over the
# first SAMPLE people of each country (an arbitrary but fixed subset) instead.
SAMPLE = 20000
SAMPLED = {("ar", "family"), ("en", "given"), ("en", "family"), ("de", "given"),
           ("de", "family"), ("fr", "given"), ("fr", "family")}


def sampled(query: str, countries: list) -> str:
    people = " UNION ".join(
        "{ SELECT ?p WHERE { ?p wdt:P27 wd:%s } LIMIT %d }" % (c, SAMPLE) for c in countries)
    # optimizer None: evaluate in the written order, the sample first
    return query.replace("VALUES ?country { %(countries)s }\n      ?p wdt:P27 ?country ;",
                         'hint:Query hint:optimizer "None" .\n      '
                         + people + "\n      ?p")


if __name__ == "__main__":
    which = sys.argv[1:] or list(COUNTRIES)
    for origin in which:
        countries = " ".join("wd:" + c for c in COUNTRIES[origin])
        for kind, q, limit in (("given", GIVEN, 400), ("family", FAMILY, 400)):
            if (origin, kind) in SAMPLED:
                query = sampled(q, COUNTRIES[origin]) % {"limit": limit}
            else:
                query = q % {"countries": countries, "limit": limit}
            (OUT / f"{origin}_{kind}.rq").write_text(query + "\n", encoding="utf-8", newline="")
            path = OUT / f"{origin}_{kind}.csv"
            if path.exists() and path.stat().st_size > 100:
                print(origin, kind, "cached"); continue
            for attempt in range(3):
                try:
                    time.sleep(70)
                    print(origin, kind, run(query, path), flush=True)
                    break
                except Exception as exc:  # noqa: BLE001
                    print(origin, kind, "ERR", type(exc).__name__, exc, flush=True)
                    time.sleep(60)
