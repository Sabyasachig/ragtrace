"""
Regression testing engine for RAGTrace.

Provides snapshot-based regression testing by comparing RAG pipeline
outputs across runs. Detects regressions in retrieval quality, answer
quality, and cost.
"""

import difflib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from .models import (
    Snapshot,
    ComparisonResult,
    RetrievalDiff,
    AnswerDiff,
    CostDiff,
)

logger = logging.getLogger(__name__)


class RegressionAnalyzer:
    """
    Compares two snapshots to detect regressions.

    Analyses three dimensions:
    1. Retrieval — which chunks appeared, disappeared, or stayed
    2. Answer    — line-level diff + cosine-like similarity score
    3. Cost      — absolute delta and percentage change
    """

    # ── Retrieval Diffing ────────────────────────────────────────────────────

    def _chunk_texts(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract normalised text from a list of chunk dicts."""
        texts = []
        for chunk in chunks:
            # Support both {"text": ...} and {"page_content": ...} shapes
            text = chunk.get("text") or chunk.get("page_content") or str(chunk)
            texts.append(text.strip())
        return texts

    def diff_retrieval(
        self,
        old_chunks: List[Dict[str, Any]],
        new_chunks: List[Dict[str, Any]],
    ) -> RetrievalDiff:
        """
        Compare two sets of retrieved chunks.

        Uses set-based comparison so chunk order does not matter.

        Args:
            old_chunks: Chunks from the baseline snapshot
            new_chunks: Chunks from the new snapshot

        Returns:
            RetrievalDiff with added / removed / unchanged lists and a
            Jaccard similarity score.
        """
        old_texts = set(self._chunk_texts(old_chunks))
        new_texts = set(self._chunk_texts(new_chunks))

        added = sorted(new_texts - old_texts)
        removed = sorted(old_texts - new_texts)
        unchanged = sorted(old_texts & new_texts)

        # Jaccard similarity: |intersection| / |union|
        union_size = len(old_texts | new_texts)
        similarity = len(unchanged) / union_size if union_size > 0 else 1.0

        return RetrievalDiff(
            added=added,
            removed=removed,
            unchanged=unchanged,
            similarity_score=round(similarity, 4),
        )

    # ── Answer Diffing ───────────────────────────────────────────────────────

    def diff_answers(self, old_answer: str, new_answer: str) -> AnswerDiff:
        """
        Compare two answer strings using unified diff.

        Args:
            old_answer: Answer from the baseline snapshot
            new_answer: Answer from the new snapshot

        Returns:
            AnswerDiff with diff lines, similarity score, and lengths.
        """
        old_lines = old_answer.splitlines(keepends=True)
        new_lines = new_answer.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile="baseline",
                tofile="current",
                lineterm="",
            )
        )

        # SequenceMatcher ratio: 0.0 (totally different) → 1.0 (identical)
        similarity = difflib.SequenceMatcher(
            None, old_answer, new_answer
        ).ratio()

        return AnswerDiff(
            diff_lines=diff_lines,
            similarity_score=round(similarity, 4),
            length_old=len(old_answer),
            length_new=len(new_answer),
        )

    # ── Cost Diffing ─────────────────────────────────────────────────────────

    def diff_costs(self, old_cost: float, new_cost: float) -> CostDiff:
        """
        Compare costs between two snapshots.

        Args:
            old_cost: Cost of the baseline snapshot in USD
            new_cost: Cost of the new snapshot in USD

        Returns:
            CostDiff with absolute delta and percent change.
        """
        delta = new_cost - old_cost
        if old_cost > 0:
            percent_change = round((delta / old_cost) * 100, 2)
        else:
            percent_change = 0.0 if new_cost == 0 else 100.0

        return CostDiff(
            old_cost=old_cost,
            new_cost=new_cost,
            delta=round(delta, 6),
            percent_change=percent_change,
        )

    # ── Full Comparison ──────────────────────────────────────────────────────

    def compare(self, snapshot1: Snapshot, snapshot2: Snapshot) -> ComparisonResult:
        """
        Perform a full comparison between two snapshots.

        Args:
            snapshot1: Baseline snapshot (older / reference)
            snapshot2: Current snapshot (new / candidate)

        Returns:
            ComparisonResult with diffs for retrieval, answer, and cost.
        """
        query_same = snapshot1.query.strip() == snapshot2.query.strip()

        retrieval_diff = self.diff_retrieval(snapshot1.chunks, snapshot2.chunks)
        answer_diff = self.diff_answers(snapshot1.answer, snapshot2.answer)
        cost_diff = self.diff_costs(snapshot1.cost, snapshot2.cost)

        return ComparisonResult(
            snapshot1_id=snapshot1.id,
            snapshot2_id=snapshot2.id,
            query_same=query_same,
            retrieval_diff=retrieval_diff,
            answer_diff=answer_diff,
            cost_diff=cost_diff,
            timestamp=datetime.utcnow(),
        )

    # ── Regression Scoring ───────────────────────────────────────────────────

    def regression_score(self, result: ComparisonResult) -> Dict[str, Any]:
        """
        Produce a human-readable regression summary from a comparison.

        Score interpretation:
        - retrieval_score: 1.0 = identical chunks, 0.0 = no overlap
        - answer_score:    1.0 = identical answers, 0.0 = completely different
        - cost_regression: True if cost increased by more than 10 %

        Args:
            result: A ComparisonResult produced by compare()

        Returns:
            Dict with per-dimension scores and an overall verdict.
        """
        retrieval_score = result.retrieval_diff.similarity_score
        answer_score = result.answer_diff.similarity_score
        cost_regression = result.cost_diff.percent_change > 10.0

        # Weighted composite (retrieval 40 %, answer 60 %)
        composite = round(0.4 * retrieval_score + 0.6 * answer_score, 4)

        verdict: str
        if composite >= 0.95 and not cost_regression:
            verdict = "PASS"
        elif composite >= 0.80:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        return {
            "verdict": verdict,
            "composite_score": composite,
            "retrieval_score": retrieval_score,
            "answer_score": answer_score,
            "cost_change_pct": result.cost_diff.percent_change,
            "cost_regression": cost_regression,
            "chunks_added": len(result.retrieval_diff.added),
            "chunks_removed": len(result.retrieval_diff.removed),
            "query_same": result.query_same,
        }

    # ── Batch Regression ─────────────────────────────────────────────────────

    def batch_compare(
        self,
        baseline: Snapshot,
        candidates: List[Snapshot],
    ) -> List[Dict[str, Any]]:
        """
        Compare a baseline snapshot against multiple candidates.

        Useful for tracking how a pipeline changes across many runs.

        Args:
            baseline: Reference snapshot
            candidates: List of snapshots to compare against the baseline

        Returns:
            List of regression score dicts, one per candidate.
        """
        results = []
        for candidate in candidates:
            comparison = self.compare(baseline, candidate)
            score = self.regression_score(comparison)
            score["snapshot_id"] = candidate.id
            score["snapshot_timestamp"] = candidate.timestamp.isoformat()
            results.append(score)
        return results


# ── Convenience helpers ───────────────────────────────────────────────────────

_analyzer: Optional[RegressionAnalyzer] = None


def get_analyzer() -> RegressionAnalyzer:
    """Return (or create) the singleton RegressionAnalyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = RegressionAnalyzer()
    return _analyzer


def compare_snapshots(snapshot1: Snapshot, snapshot2: Snapshot) -> ComparisonResult:
    """Convenience function: compare two snapshots and return the full result."""
    return get_analyzer().compare(snapshot1, snapshot2)


def score_regression(snapshot1: Snapshot, snapshot2: Snapshot) -> Dict[str, Any]:
    """Convenience function: compare two snapshots and return a score summary."""
    result = compare_snapshots(snapshot1, snapshot2)
    return get_analyzer().regression_score(result)
