"""Batch-level health monitoring and automatic stop conditions.

The audited pipeline had exactly two stall guards -- an attempt budget and a
consecutive-empty-batch counter -- both of which only fire when generation has
already collapsed. Everything between "working perfectly" and "producing
nothing" was unmonitored, which is how a run produced 1,583 duplicate-id
rejections (50.7% of all rejections) across two resumes without anything
noticing.

This module adds the middle ground: a set of named thresholds evaluated after
every batch, each with a `warn` level that logs and a `stop` level that halts
the run cleanly.

Stopping is deliberately conservative about what it does. On a stop condition
the pipeline finishes the current batch (its results are already paid for),
persists state, writes a report, and exits. It never discards completed work
and never resumes by itself -- a stop means a human needs to look.

Baselines in DEFAULT_THRESHOLDS are measured from the 28,560-record corpus,
not guessed. Where a metric had no baseline it is marked provisional in the
comment and should be recalibrated after the 5,000-document pilot.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("piigen.llm.monitor")


@dataclass
class Threshold:
    """One monitored metric.

    `higher_is_worse` flips the comparison for metrics like throughput, where
    a LOW number is the problem. `warn`/`stop` may be None for a metric that
    only has one meaningful level (a span mismatch has no acceptable rate).
    """

    name: str
    warn: float | None
    stop: float | None
    higher_is_worse: bool = True
    unit: str = ""
    note: str = ""
    # Ratios computed over a handful of attempts are noise, not signal: a
    # 6-document batch that accepts 1 reads as a 17% acceptance rate and
    # would trip the 30% stop level on its own. Rate metrics therefore need
    # a minimum sample before they are scored at all; absolute counts (a
    # span mismatch, a forbidden label, a failed write) are scored from the
    # very first observation, because for those even one is too many.
    min_samples: int = 0

    def evaluate(self, value: float, samples: int = 0) -> str:
        if samples < self.min_samples:
            return "ok"
        def breached(limit: float | None) -> bool:
            if limit is None:
                return False
            return value > limit if self.higher_is_worse else value < limit

        if breached(self.stop):
            return "stop"
        if breached(self.warn):
            return "warn"
        return "ok"


# Baselines, warn and stop levels. See the audit report section I.
DEFAULT_THRESHOLDS: dict[str, Threshold] = {
    "acceptance_rate": Threshold(
        "acceptance_rate", warn=0.50, stop=0.30, higher_is_worse=False,
        unit="share", note="corpus baseline 0.675", min_samples=120),
    "span_mismatch": Threshold(
        "span_mismatch", warn=None, stop=0, unit="count",
        note="baseline 0 in 124,348 spans -- any nonzero is a hard stop"),
    "forbidden_label": Threshold(
        "forbidden_label", warn=None, stop=0, unit="count",
        note="a removed/unknown label reaching output is a policy breach"),
    "duplicate_id_rejects": Threshold(
        "duplicate_id_rejects", warn=10, stop=100, unit="per batch",
        note="corpus carried 1,583 total from two resume collisions"),
    "near_duplicate_rate": Threshold(
        "near_duplicate_rate", warn=0.01, stop=0.05, unit="share",
        note="corpus baseline 0.0002", min_samples=120),
    "pool_over_cap_share": Threshold(
        "pool_over_cap_share", warn=0.02, stop=0.10, unit="share",
        note="worst label; simulated CITY at 100k was 0.31", min_samples=200),
    "label_share_drift_low": Threshold(
        "label_share_drift_low", warn=0.6, stop=0.4, higher_is_worse=False,
        unit="x target", note="corpus range was 0.84-1.23x", min_samples=500),
    "label_share_drift_high": Threshold(
        "label_share_drift_high", warn=1.6, stop=2.5, unit="x target",
        note="corpus range was 0.84-1.23x", min_samples=500),
    "english_contamination": Threshold(
        "english_contamination", warn=0.03, stop=0.08, unit="share",
        note="corpus baseline 0.0057; PROVISIONAL detector", min_samples=120),
    "validator_failure_rate": Threshold(
        "validator_failure_rate", warn=0.02, stop=0.10, unit="share",
        note="corpus baseline 0.0 on re-validation", min_samples=120),
    "api_error_rate": Threshold(
        "api_error_rate", warn=0.05, stop=0.20, unit="share",
        note="corpus baseline 0.0003", min_samples=120),
    "throughput_per_hour": Threshold(
        "throughput_per_hour", warn=250, stop=100, higher_is_worse=False,
        unit="accepted/h", note="observed 497/h at concurrency 5", min_samples=120),
    "output_write_failure": Threshold(
        "output_write_failure", warn=None, stop=0, unit="count"),
    "checkpoint_divergence_batches": Threshold(
        "checkpoint_divergence_batches", warn=1, stop=3, unit="batches",
        note="corpus was 7,633 records / 21,011 indices diverged"),
}


@dataclass
class BatchMetrics:
    """One batch's observations. Every field is a raw count or a ratio."""

    batch_no: int = 0
    attempted: int = 0
    accepted: int = 0
    span_mismatch: int = 0
    forbidden_label: int = 0
    duplicate_id_rejects: int = 0
    near_duplicate_rejects: int = 0
    validator_rejects: int = 0
    api_errors: int = 0
    english_rejects: int = 0
    output_write_failure: int = 0
    pool_over_cap_share: float = 0.0
    pool_stop_labels: list = field(default_factory=list)
    label_share_drift: dict = field(default_factory=dict)
    throughput_per_hour: float = 0.0
    checkpoint_divergence_batches: int = 0
    mean_text_length: float = 0.0
    elapsed: float = 0.0
    # Cumulative counters for the run so far. Sample sizes are judged
    # against these, not against the single batch: the question a threshold
    # asks is "is this run drifting?", and one batch of 6 cannot answer it.
    total_attempted: int = 0
    total_mentions: int = 0
    total_pool_draws: int = 0

    def sample_counts(self) -> dict:
        """How much evidence stands behind each metric."""
        attempts = self.total_attempted or self.attempted
        return {
            "acceptance_rate": attempts,
            "near_duplicate_rate": attempts,
            "english_contamination": attempts,
            "validator_failure_rate": attempts,
            "api_error_rate": attempts,
            "throughput_per_hour": attempts,
            "pool_over_cap_share": self.total_pool_draws,
            "label_share_drift_low": self.total_mentions,
            "label_share_drift_high": self.total_mentions,
        }

    def as_metric_values(self) -> dict:
        """Flatten to the {threshold_name: value} shape the monitor scores."""
        attempted = max(1, self.attempted)
        drifts = list(self.label_share_drift.values()) or [1.0]
        return {
            "acceptance_rate": self.accepted / attempted,
            "span_mismatch": self.span_mismatch,
            "forbidden_label": self.forbidden_label,
            "duplicate_id_rejects": self.duplicate_id_rejects,
            "near_duplicate_rate": self.near_duplicate_rejects / attempted,
            "pool_over_cap_share": self.pool_over_cap_share,
            "label_share_drift_low": min(drifts),
            "label_share_drift_high": max(drifts),
            "english_contamination": self.english_rejects / attempted,
            "validator_failure_rate": self.validator_rejects / attempted,
            "api_error_rate": self.api_errors / attempted,
            "throughput_per_hour": self.throughput_per_hour,
            "output_write_failure": self.output_write_failure,
            "checkpoint_divergence_batches": self.checkpoint_divergence_batches,
        }


class RunMonitor:
    """Scores each batch against the thresholds and decides warn/stop.

    Holds the full per-batch history so the end-of-run report can show a
    trend rather than only the final state -- a metric drifting steadily
    toward its stop level across ten batches is a different problem from one
    that spiked once, and the distinction is invisible without history.
    """

    # Rate metrics smoothed across this run's own batch history rather than
    # judged on one batch alone -- see the comment on `_smoothed_values`.
    # Maps threshold name -> the BatchMetrics field that is its numerator.
    _SMOOTHED_RATES = {
        "acceptance_rate": "accepted",
        "near_duplicate_rate": "near_duplicate_rejects",
        "english_contamination": "english_rejects",
        "validator_failure_rate": "validator_rejects",
        "api_error_rate": "api_errors",
    }

    # Ceiling on how much smoothing "weight" _cum_attempted may carry,
    # rescaled back down proportionally once crossed (see
    # `_smoothed_values`'s second paragraph) -- what makes it safe to
    # persist this state across resumes (added the same day this was first
    # built, after the exact single-batch-noise false stop this smoothing
    # exists to prevent recurred on the very first batch of three separate
    # fresh restarts in a row). Persisting unboundedly would let decades of
    # good history mask a real regression starting today; capping the
    # weight means a sustained new problem still moves the smoothed rate
    # within a bounded number of future batches, on the order of this
    # ceiling / batch_size, not "eventually, after enough of the whole
    # project's lifetime accumulates."
    _SMOOTHING_CEILING = 2000

    def __init__(self, thresholds: dict | None = None,
                 report_path: Path | None = None,
                 smoothing_state: dict | None = None) -> None:
        self.thresholds = dict(thresholds or DEFAULT_THRESHOLDS)
        self.report_path = Path(report_path) if report_path else None
        self.history: list[dict] = []
        self.stop_reasons: list[str] = []
        self.warn_counts: dict[str, int] = {}
        self.started = time.time()
        # 2026-08-27 audit: realized-vs-target label drift.
        #
        # `assemble_document` accepts a document that dropped up to HALF its
        # planned values, so the corpus's actual label mix silently diverges
        # from the configured `entity_weights`. Measured over 65,690 records:
        # 3,320 planned values never appeared in text at all (2,549 records),
        # 2,716 of them the four ml_context labels -- GIVENNAME 873,
        # SURNAME 770, STREET 622, CITY 451. Nothing aggregated that, because
        # the missing-value rule is per-document.
        self.planned_labels: dict[str, int] = {}
        self.realized_labels: dict[str, int] = {}
        # 2026-08-26: cumulative numerator/denominator for each rate in
        # _SMOOTHED_RATES. Originally scoped to THIS RunMonitor instance
        # only (i.e. reset on every resume) -- see the fix note on
        # _smoothed_values for the original problem this solves. That
        # scoping traded one bug for a smaller one: a FRESH process's batch
        # 1 has nothing to smooth against yet, so it is judged alone again,
        # exactly like before this fix existed -- confirmed live when the
        # false stop this fix targets recurred on batch 1 of three separate
        # resumes the same day. `smoothing_state` (passed in on resume,
        # from the checkpoint -- see checkpoint.py's RunState.rate_smoothing)
        # carries real smoothing weight across a resume instead of
        # discarding it, bounded by _SMOOTHING_CEILING so it still cannot
        # mask a genuine new regression indefinitely.
        self._cum_attempted = 0
        self._cum: dict[str, int] = {}
        if smoothing_state:
            self._cum_attempted = int(smoothing_state.get("cum_attempted", 0))
            self._cum = {k: int(v) for k, v in
                         (smoothing_state.get("cum") or {}).items()
                         if k in self._SMOOTHED_RATES}

    def export_smoothing_state(self) -> dict:
        """Checkpoint-safe snapshot of the cumulative rate state -- see
        `smoothing_state` on __init__ for why this is persisted."""
        return {"cum_attempted": self._cum_attempted, "cum": dict(self._cum)}

    def _smoothed_values(self, metrics: BatchMetrics, values: dict) -> dict:
        """Replace single-batch ratios with cumulative ones.

        2026-08-26: `min_samples` (BatchMetrics.sample_counts()) already
        gated these five rates on cumulative attempts, matching this
        class's own docstring -- "the question a threshold asks is 'is this
        run drifting?', and one batch ... cannot answer it" -- but the VALUE
        being judged against warn/stop was still `metrics.as_metric_values()`
        alone, a single ~100-attempt batch's own raw ratio. The gate and the
        value it gated disagreed: min_samples opens after ~2 batches
        (cumulative attempts satisfy it fast), yet every batch after that
        was still scored on its own noisy 100-attempt sample forever.
        Confirmed live: english_contamination hit 0.09 (over its 0.08 stop
        level) on a single batch whose own rejected documents, read
        directly, were genuine Azerbaijani text (informal/diacritic-free
        spelling), not contamination -- exactly the kind of false stop
        batch-level noise produces.
        """
        self._cum_attempted += metrics.attempted
        out = dict(values)
        if self._cum_attempted == 0:
            return out
        for name, field_name in self._SMOOTHED_RATES.items():
            self._cum[name] = self._cum.get(name, 0) + getattr(metrics, field_name)
            out[name] = self._cum[name] / self._cum_attempted
        # Rescale down once the ceiling is crossed -- see _SMOOTHING_CEILING.
        # Every count shrinks by the same factor, so every ratio in `out`
        # above (already computed from the pre-rescale counts) is
        # unaffected; only how much future weight this history carries
        # changes.
        if self._cum_attempted > self._SMOOTHING_CEILING:
            factor = self._SMOOTHING_CEILING / self._cum_attempted
            self._cum_attempted = self._SMOOTHING_CEILING
            self._cum = {k: v * factor for k, v in self._cum.items()}
        return out

    def observe(self, metrics: BatchMetrics) -> str:
        """Score one batch. Returns 'ok', 'warn' or 'stop'."""
        values = self._smoothed_values(metrics, metrics.as_metric_values())
        sample_counts = metrics.sample_counts()
        statuses, breaches = {}, []
        worst = "ok"

        for name, value in values.items():
            threshold = self.thresholds.get(name)
            if threshold is None:
                continue
            status = threshold.evaluate(value, samples=sample_counts.get(name, 0))
            statuses[name] = status
            if status == "warn":
                self.warn_counts[name] = self.warn_counts.get(name, 0) + 1
                worst = "stop" if worst == "stop" else "warn"
                breaches.append((name, value, threshold, status))
            elif status == "stop":
                worst = "stop"
                breaches.append((name, value, threshold, status))

        entry = {
            "batch": metrics.batch_no,
            "timestamp": time.time(),
            "values": values,
            "statuses": statuses,
            "status": worst,
            "pool_stop_labels": list(metrics.pool_stop_labels),
            "mean_text_length": metrics.mean_text_length,
        }
        self.history.append(entry)

        for name, value, threshold, status in breaches:
            limit = threshold.stop if status == "stop" else threshold.warn
            direction = "above" if threshold.higher_is_worse else "below"
            message = (f"{name}={value:.4g} is {direction} its {status} "
                       f"level {limit:.4g} {threshold.unit}".strip())
            if threshold.note:
                message += f" ({threshold.note})"
            if status == "stop":
                log.error("STOP CONDITION -- batch %d: %s",
                          metrics.batch_no, message)
                self.stop_reasons.append(f"batch {metrics.batch_no}: {message}")
            else:
                log.warning("batch %d: %s", metrics.batch_no, message)

        if metrics.pool_stop_labels:
            reason = ("value pool over-cap beyond the stop share for: "
                      + ", ".join(metrics.pool_stop_labels))
            log.error("STOP CONDITION -- batch %d: %s",
                      metrics.batch_no, reason)
            self.stop_reasons.append(f"batch {metrics.batch_no}: {reason}")
            worst = "stop"
            entry["status"] = "stop"

        return worst

    @property
    def should_stop(self) -> bool:
        return bool(self.stop_reasons)

    def record_label_outcome(self, planned: list, realized: list) -> None:
        """Accumulate what a document ASKED for versus what it got.

        `planned` is the spec's entity labels, `realized` the labels actually
        resolved into spans. Called once per accepted document.
        """
        for label in planned:
            self.planned_labels[label] = self.planned_labels.get(label, 0) + 1
        for label in realized:
            self.realized_labels[label] = self.realized_labels.get(label, 0) + 1

    def label_drift(self) -> dict:
        """Per-label planned vs realized, worst shortfall first.

        Reported, never enforced: some divergence is expected because
        `complete_occurrences` legitimately labels repeat mentions, which can
        push realized ABOVE planned. What matters is a persistent shortfall,
        which means the configured distribution is not the one being built.
        """
        out = {}
        for label in sorted(set(self.planned_labels) | set(self.realized_labels)):
            planned = self.planned_labels.get(label, 0)
            realized = self.realized_labels.get(label, 0)
            out[label] = {
                "planned": planned,
                "realized": realized,
                "delta": realized - planned,
                "realized_pct_of_planned": (
                    round(100 * realized / planned, 1) if planned else None),
            }
        return dict(sorted(
            out.items(),
            key=lambda kv: (kv[1]["realized_pct_of_planned"]
                            if kv[1]["realized_pct_of_planned"] is not None
                            else 1e9)))

    def report(self) -> dict:
        return {
            "label_drift": self.label_drift(),
            "started": self.started,
            "elapsed_seconds": time.time() - self.started,
            "batches": len(self.history),
            "status": "stop" if self.should_stop else (
                "warn" if self.warn_counts else "ok"),
            "stop_reasons": list(self.stop_reasons),
            "warn_counts": dict(self.warn_counts),
            "thresholds": {
                name: {"warn": t.warn, "stop": t.stop,
                       "higher_is_worse": t.higher_is_worse,
                       "unit": t.unit, "note": t.note}
                for name, t in self.thresholds.items()},
            "history": self.history,
        }

    def write_report(self) -> Path | None:
        if not self.report_path:
            return None
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(self.report(), ensure_ascii=False, indent=2),
            encoding="utf-8")
        return self.report_path
