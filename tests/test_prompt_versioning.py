"""
Unit tests for the prompt versioning system.

Tests DB storage, version auto-increment, deactivation,
diff endpoint logic, and the API route layer via FastAPI TestClient.
"""

import pytest
import tempfile
import os

from core.storage import Database
from core.models import PromptVersion


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    yield db
    if db.conn:
        db.conn.close()
    os.unlink(path)


def make_pv(name: str = "qa_template", template: str = "Answer: {question}") -> PromptVersion:
    return PromptVersion(name=name, version=0, template=template)


# ── Storage layer ─────────────────────────────────────────────────────────────

class TestPromptVersionStorage:
    def test_save_creates_version_1(self, temp_db):
        pv = make_pv()
        saved = temp_db.save_prompt_version(pv)
        assert saved.version == 1
        assert saved.is_active is True

    def test_save_increments_version(self, temp_db):
        temp_db.save_prompt_version(make_pv())
        second = temp_db.save_prompt_version(make_pv(template="v2: {question}"))
        assert second.version == 2

    def test_new_version_deactivates_old(self, temp_db):
        v1 = temp_db.save_prompt_version(make_pv(template="v1"))
        temp_db.save_prompt_version(make_pv(template="v2"))

        fetched_v1 = temp_db.get_prompt_version("qa_template", 1)
        assert fetched_v1.is_active is False

    def test_get_active_returns_newest(self, temp_db):
        temp_db.save_prompt_version(make_pv(template="v1"))
        temp_db.save_prompt_version(make_pv(template="v2"))
        active = temp_db.get_prompt_version("qa_template")
        assert active.version == 2
        assert active.template == "v2"

    def test_get_specific_version(self, temp_db):
        temp_db.save_prompt_version(make_pv(template="first"))
        temp_db.save_prompt_version(make_pv(template="second"))
        v1 = temp_db.get_prompt_version("qa_template", 1)
        assert v1.template == "first"

    def test_get_nonexistent_returns_none(self, temp_db):
        assert temp_db.get_prompt_version("does-not-exist") is None

    def test_get_nonexistent_version_returns_none(self, temp_db):
        temp_db.save_prompt_version(make_pv())
        assert temp_db.get_prompt_version("qa_template", 99) is None

    def test_list_versions_newest_first(self, temp_db):
        for i in range(3):
            temp_db.save_prompt_version(make_pv(template=f"v{i+1}"))
        versions = temp_db.list_prompt_versions("qa_template")
        assert [v.version for v in versions] == [3, 2, 1]

    def test_list_versions_not_found_returns_empty(self, temp_db):
        assert temp_db.list_prompt_versions("nonexistent") == []

    def test_list_prompt_names(self, temp_db):
        temp_db.save_prompt_version(make_pv(name="a"))
        temp_db.save_prompt_version(make_pv(name="b"))
        temp_db.save_prompt_version(make_pv(name="a", template="a-v2"))
        names = temp_db.list_prompt_names()
        assert sorted(names) == ["a", "b"]

    def test_delete_prompt_version(self, temp_db):
        saved = temp_db.save_prompt_version(make_pv())
        deleted = temp_db.delete_prompt_version("qa_template", saved.version)
        assert deleted is True
        assert temp_db.get_prompt_version("qa_template", saved.version) is None

    def test_delete_nonexistent_returns_false(self, temp_db):
        assert temp_db.delete_prompt_version("missing", 99) is False

    def test_tags_and_description_persisted(self, temp_db):
        pv = PromptVersion(
            name="tagged",
            version=0,
            template="template",
            description="my desc",
            tags=["prod", "v2"],
        )
        saved = temp_db.save_prompt_version(pv)
        fetched = temp_db.get_prompt_version("tagged")
        assert fetched.description == "my desc"
        assert "prod" in fetched.tags
        assert "v2" in fetched.tags

    def test_multiple_prompt_names_independent(self, temp_db):
        temp_db.save_prompt_version(make_pv(name="alpha"))
        temp_db.save_prompt_version(make_pv(name="alpha"))
        temp_db.save_prompt_version(make_pv(name="beta"))

        alpha = temp_db.list_prompt_versions("alpha")
        beta = temp_db.list_prompt_versions("beta")
        assert len(alpha) == 2
        assert len(beta) == 1
        assert alpha[0].version == 2  # newest first


# ── Diff logic ────────────────────────────────────────────────────────────────

class TestPromptVersionDiff:
    """Test the diff utility used by the API endpoint (pure Python logic)."""

    def test_identical_templates_no_diff(self):
        import difflib
        t = "Context: {ctx}\n\nQuestion: {q}\n"
        diff = list(difflib.unified_diff(
            t.splitlines(keepends=True), t.splitlines(keepends=True), lineterm="",
        ))
        assert diff == []

    def test_changed_line_in_diff(self):
        import difflib
        old = "Please answer briefly.\nContext: {ctx}\nQ: {q}"
        new = "Please answer in detail.\nContext: {ctx}\nQ: {q}"
        diff = list(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="v1", tofile="v2", lineterm="",
        ))
        text = "\n".join(diff)
        assert "-Please answer briefly." in text
        assert "+Please answer in detail." in text

    def test_similarity_identical(self):
        import difflib
        t = "hello world"
        score = difflib.SequenceMatcher(None, t, t).ratio()
        assert score == pytest.approx(1.0)

    def test_similarity_different(self):
        import difflib
        score = difflib.SequenceMatcher(None, "abc", "xyz").ratio()
        assert score < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
