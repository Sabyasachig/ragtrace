"""
Unit tests for the regression analysis engine.

Tests snapshot diffing for retrieval, answer, and cost dimensions,
as well as the regression scoring and batch comparison features.
"""

import pytest
from datetime import datetime

from core.regression import RegressionAnalyzer, compare_snapshots, score_regression
from core.models import Snapshot, ComparisonResult


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_snapshot(
    query: str = "What is RAG?",
    chunks: list | None = None,
    answer: str = "RAG is Retrieval-Augmented Generation.",
    cost: float = 0.005,
) -> Snapshot:
    if chunks is None:
        chunks = [
            {"text": "RAG combines retrieval and generation.", "metadata": {"score": 0.9}},
            {"text": "Vector databases power retrieval.", "metadata": {"score": 0.8}},
        ]
    return Snapshot(
        session_id="test-session",
        query=query,
        chunks=chunks,
        answer=answer,
        cost=cost,
        timestamp=datetime.utcnow(),
    )


# ── RegressionAnalyzer: retrieval ─────────────────────────────────────────────

class TestRetrievalDiff:
    def setup_method(self):
        self.analyzer = RegressionAnalyzer()

    def test_identical_chunks_full_similarity(self):
        chunks = [{"text": "chunk A"}, {"text": "chunk B"}]
        result = self.analyzer.diff_retrieval(chunks, chunks)
        assert result.similarity_score == 1.0
        assert result.added == []
        assert result.removed == []
        assert len(result.unchanged) == 2

    def test_completely_different_chunks_zero_similarity(self):
        old = [{"text": "chunk A"}]
        new = [{"text": "chunk B"}]
        result = self.analyzer.diff_retrieval(old, new)
        assert result.similarity_score == 0.0
        assert len(result.added) == 1
        assert len(result.removed) == 1
        assert result.unchanged == []

    def test_partial_overlap(self):
        old = [{"text": "shared chunk"}, {"text": "old only"}]
        new = [{"text": "shared chunk"}, {"text": "new only"}]
        result = self.analyzer.diff_retrieval(old, new)
        assert result.similarity_score == pytest.approx(1 / 3, abs=0.01)
        assert "shared chunk" in result.unchanged
        assert "new only" in result.added
        assert "old only" in result.removed

    def test_empty_old_chunks(self):
        new = [{"text": "something new"}]
        result = self.analyzer.diff_retrieval([], new)
        assert result.similarity_score == 0.0
        assert len(result.added) == 1

    def test_empty_both_chunks(self):
        result = self.analyzer.diff_retrieval([], [])
        assert result.similarity_score == 1.0

    def test_page_content_key_supported(self):
        old = [{"page_content": "chunk A"}]
        new = [{"page_content": "chunk A"}]
        result = self.analyzer.diff_retrieval(old, new)
        assert result.similarity_score == 1.0


# ── RegressionAnalyzer: answer ────────────────────────────────────────────────

class TestAnswerDiff:
    def setup_method(self):
        self.analyzer = RegressionAnalyzer()

    def test_identical_answers(self):
        answer = "RAG is great."
        result = self.analyzer.diff_answers(answer, answer)
        assert result.similarity_score == 1.0
        assert result.diff_lines == []

    def test_completely_different_answers(self):
        result = self.analyzer.diff_answers("Hello world", "Goodbye universe")
        assert result.similarity_score < 0.5
        assert len(result.diff_lines) > 0

    def test_minor_change_high_similarity(self):
        old = "RAG is Retrieval-Augmented Generation, a technique for LLMs."
        new = "RAG is Retrieval-Augmented Generation, a technique for large language models."
        result = self.analyzer.diff_answers(old, new)
        assert result.similarity_score > 0.7

    def test_length_fields(self):
        old = "short"
        new = "a much longer answer here"
        result = self.analyzer.diff_answers(old, new)
        assert result.length_old == len(old)
        assert result.length_new == len(new)

    def test_empty_old_answer(self):
        result = self.analyzer.diff_answers("", "new answer")
        assert result.similarity_score == 0.0
        assert result.length_old == 0

    def test_diff_lines_contain_plus_minus(self):
        result = self.analyzer.diff_answers("old line\n", "new line\n")
        text = "\n".join(result.diff_lines)
        assert "-old line" in text
        assert "+new line" in text


# ── RegressionAnalyzer: cost ──────────────────────────────────────────────────

class TestCostDiff:
    def setup_method(self):
        self.analyzer = RegressionAnalyzer()

    def test_identical_cost(self):
        result = self.analyzer.diff_costs(0.01, 0.01)
        assert result.delta == pytest.approx(0.0)
        assert result.percent_change == pytest.approx(0.0)

    def test_cost_increase(self):
        result = self.analyzer.diff_costs(0.01, 0.02)
        assert result.delta == pytest.approx(0.01)
        assert result.percent_change == pytest.approx(100.0)

    def test_cost_decrease(self):
        result = self.analyzer.diff_costs(0.02, 0.01)
        assert result.delta == pytest.approx(-0.01)
        assert result.percent_change == pytest.approx(-50.0)

    def test_zero_baseline_new_cost(self):
        result = self.analyzer.diff_costs(0.0, 0.005)
        assert result.percent_change == 100.0

    def test_both_zero_cost(self):
        result = self.analyzer.diff_costs(0.0, 0.0)
        assert result.percent_change == 0.0


# ── Full comparison ───────────────────────────────────────────────────────────

class TestFullComparison:
    def setup_method(self):
        self.analyzer = RegressionAnalyzer()

    def test_identical_snapshots(self):
        snap = make_snapshot()
        result = self.analyzer.compare(snap, snap)
        assert isinstance(result, ComparisonResult)
        assert result.query_same is True
        assert result.retrieval_diff.similarity_score == 1.0
        assert result.answer_diff.similarity_score == 1.0
        assert result.cost_diff.delta == pytest.approx(0.0)

    def test_different_queries_flagged(self):
        snap1 = make_snapshot(query="What is RAG?")
        snap2 = make_snapshot(query="How does RAG work?")
        result = self.analyzer.compare(snap1, snap2)
        assert result.query_same is False

    def test_different_answers_detected(self):
        snap1 = make_snapshot(answer="Old answer.")
        snap2 = make_snapshot(answer="Completely new answer that is very different.")
        result = self.analyzer.compare(snap1, snap2)
        assert result.answer_diff.similarity_score < 1.0

    def test_cost_increase_detected(self):
        snap1 = make_snapshot(cost=0.01)
        snap2 = make_snapshot(cost=0.05)
        result = self.analyzer.compare(snap1, snap2)
        assert result.cost_diff.delta == pytest.approx(0.04, abs=1e-9)

    def test_compare_snapshots_convenience(self):
        snap1 = make_snapshot()
        snap2 = make_snapshot(answer="Slightly different answer here.")
        result = compare_snapshots(snap1, snap2)
        assert isinstance(result, ComparisonResult)


# ── Regression scoring ────────────────────────────────────────────────────────

class TestRegressionScore:
    def setup_method(self):
        self.analyzer = RegressionAnalyzer()

    def test_identical_snapshots_pass(self):
        snap = make_snapshot()
        result = self.analyzer.compare(snap, snap)
        score = self.analyzer.regression_score(result)
        assert score["verdict"] == "PASS"
        assert score["composite_score"] == pytest.approx(1.0)

    def test_major_regression_fail(self):
        snap1 = make_snapshot(
            chunks=[{"text": "totally different context A"}],
            answer="Answer A which is very specific.",
            cost=0.001,
        )
        snap2 = make_snapshot(
            chunks=[{"text": "totally different context B"}],
            answer="Completely unrelated answer B, nothing in common.",
            cost=0.001,
        )
        result = self.analyzer.compare(snap1, snap2)
        score = self.analyzer.regression_score(result)
        assert score["verdict"] in ("FAIL", "WARN")

    def test_score_keys_present(self):
        snap = make_snapshot()
        result = self.analyzer.compare(snap, snap)
        score = self.analyzer.regression_score(result)
        for key in ("verdict", "composite_score", "retrieval_score", "answer_score",
                    "cost_change_pct", "cost_regression", "chunks_added",
                    "chunks_removed", "query_same"):
            assert key in score

    def test_score_regression_convenience(self):
        snap = make_snapshot()
        score = score_regression(snap, snap)
        assert score["verdict"] == "PASS"


# ── Batch compare ─────────────────────────────────────────────────────────────

class TestBatchCompare:
    def setup_method(self):
        self.analyzer = RegressionAnalyzer()

    def test_batch_returns_one_per_candidate(self):
        baseline = make_snapshot()
        candidates = [make_snapshot(answer=f"Answer variant {i}") for i in range(4)]
        results = self.analyzer.batch_compare(baseline, candidates)
        assert len(results) == 4

    def test_batch_includes_snapshot_id(self):
        baseline = make_snapshot()
        candidates = [make_snapshot()]
        results = self.analyzer.batch_compare(baseline, candidates)
        assert "snapshot_id" in results[0]
        assert "snapshot_timestamp" in results[0]

    def test_empty_candidates(self):
        baseline = make_snapshot()
        results = self.analyzer.batch_compare(baseline, [])
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
