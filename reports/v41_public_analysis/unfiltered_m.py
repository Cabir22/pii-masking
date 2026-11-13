"""v4.2 analysis: eval/scoreboard.py with track M's validity-2 filter
switched off (D-64b), so its effect can be read: track M without
predict._drop_impossible_values ("M0") against track M as shipped.

    python reports/v41_public_analysis/unfiltered_m.py --model your-hf-org/masking-az-runb-v4.2-seed42 \
        --revision <full SHA> --sets probes,benchmark --tracks M --name v42_M0 --out-dir <dir>

The arguments are scoreboard.py's. Predictions go to their own cache
(~/.cache/pii-scoreboard-unfiltered), never to the scoreboard's, and the
report's track M is the unfiltered one. model/ is not changed: the filter
is replaced in this process only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "model")]
import predict  # noqa: E402
import scoreboard as SB  # noqa: E402

CACHE = Path.home() / ".cache" / "pii-scoreboard-unfiltered"


def unfiltered() -> None:
    predict._drop_impossible_values = lambda spans, text: spans
    predict.DECODER_VERSION = predict.DECODER_VERSION + "-filter-off"


if __name__ == "__main__":
    if any(x.startswith("--cache-dir") for x in sys.argv):
        sys.exit("unfiltered_m.py sets its own --cache-dir")
    unfiltered()
    sys.exit(SB.main(sys.argv[1:] + ["--cache-dir", str(CACHE)]))
