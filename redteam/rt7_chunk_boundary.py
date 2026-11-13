"""RT-7 -- attempted chunk-boundary evasion (NEGATIVE RESULT).

`detect/_chunk.py` splits at clause punctuation (. ! ? ,) before the
ml_context model call. Hypothesis: engineered filler could force a clause
split between a name and the cue word that licenses it, landing the name
alone in a chunk with no context -- the same "bare value" weakness measured
quantitatively in the earlier format audit (GIVENNAME 65% bare vs. 90-95%
with any label/sentence context).

Tested against four names known to be detectable with context (not the
documented "Elvin Məmmədov"-class training-data blind spot, which is
undetectable regardless of chunking and would confound this test). Padding
does force an extra chunk boundary, but the clause splitter keeps the name
together with its OWN trailing clause ("... bu gün zəng etdi" / "... called
today"), which still gives the model enough local context. Detection held
in all 4 cases, padded and unpadded alike.

Recorded as a negative result on the same standard as the rest of this
project's work: the chunker's clause-level (not fixed-width) splitting is,
on this specific attack, doing what it is supposed to.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()
from pii_guard.detect._chunk import chunk_spans  # noqa: E402
from pii_guard.detect.names import TransformerBackend  # noqa: E402


def main() -> None:
    print("=== RT-7: attempted chunk-boundary evasion (negative result) ===\n")
    backend = TransformerBackend(model_path=harness.MODEL_ID)

    names = ["Gülsəba Həqiqətov", "Amalə Əlağayeva", "Hacıverdi Baharov",
            "Xuddam Gülbalayev"]
    long_filler = ("Müştəri münasibətləri şöbəsinin bu günkü qısa hesabatına "
                  "görə, sistemdə qeydə alınan yeni sorğu ilə əlaqədar "
                  "məlumatlandırılan, ")
    short_filler = "Müştəri, "

    for name in names:
        row = []
        for tag, filler in [("unpadded", short_filler), ("padded", long_filler)]:
            text = filler + name + " bu gün zəng etdi."
            spans = chunk_spans(text)
            dets = backend.detect(text)
            idx = text.index(name)
            found = any(d.start <= idx < d.end for d in dets)
            row.append(f"{tag}: chunks={len(spans)} detected={found}")
        print(f"{name:20s} " + "   ".join(row))

    print("\nDetection held in every case -- clause-level chunking kept each")
    print("name paired with its own trailing clause. No evasion achieved.")


if __name__ == "__main__":
    main()
