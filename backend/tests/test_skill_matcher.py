"""Unit tests for the deterministic skill matcher."""

from __future__ import annotations

import pytest

from app.services.skill_matcher import (
    compute_skill_match,
    normalize_skill,
    report_to_dict,
)


class TestNormalizeSkill:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("React", "react"),
            ("ReactJS", "react"),
            ("react.js", "react"),
            ("REACT JS", "react"),
            ("nodejs", "node.js"),
            ("Node", "node.js"),
            ("Postgres", "postgresql"),
            ("psql", "postgresql"),
            ("k8s", "kubernetes"),
            ("ts", "typescript"),
            ("tailwindcss", "tailwind css"),
        ],
    )
    def test_aliases_normalize_to_canonical(self, raw: str, expected: str) -> None:
        assert normalize_skill(raw) == expected

    def test_unknown_skill_returns_lowercased_self(self) -> None:
        assert normalize_skill("Rust") == "rust"
        assert normalize_skill("  Custom Skill  ") == "custom skill"


class TestComputeSkillMatch:
    def _resume(self, **overrides) -> dict:
        base = {
            "name": "Test Person",
            "summary": "Backend engineer with 5y experience.",
            "skills": ["Python", "FastAPI", "Postgres"],
            "experience": [
                {
                    "company": "Acme",
                    "role": "Backend Engineer",
                    "duration": "2021-Present",
                    "highlights": ["Built REST APIs in Python and FastAPI."],
                }
            ],
            "education": [],
        }
        base.update(overrides)
        return base

    def test_empty_required_returns_zero_recall(self) -> None:
        report = compute_skill_match([], self._resume())
        assert report.matched_skills == []
        assert report.missing_skills == []
        assert report.recall == 0.0

    def test_all_required_matched(self) -> None:
        report = compute_skill_match(
            ["Python", "FastAPI", "PostgreSQL"], self._resume()
        )
        assert report.matched_skills == ["python", "fastapi", "postgresql"]
        assert report.missing_skills == []
        assert report.recall == 1.0
        assert "python" in report.evidence

    def test_alias_recognition(self) -> None:
        # JD asks for "Postgres"; resume mentions "Postgres" — already canonical.
        # JD asks for "ReactJS"; resume mentions "React.js".
        resume = self._resume(skills=["React.js"], experience=[])
        report = compute_skill_match(["ReactJS"], resume)
        assert report.matched_skills == ["react"]
        assert report.recall == 1.0

    def test_missing_skill_appears_in_missing_list(self) -> None:
        report = compute_skill_match(["Python", "Kubernetes"], self._resume())
        assert "python" in report.matched_skills
        assert "kubernetes" in report.missing_skills
        assert report.recall == 0.5

    def test_evidence_quote_returned_for_matches(self) -> None:
        report = compute_skill_match(["FastAPI"], self._resume())
        assert "fastapi" in report.evidence
        # Evidence should be a non-empty quote shorter than 200 chars.
        quote = report.evidence["fastapi"]
        assert quote
        assert len(quote) < 200

    def test_match_in_highlight_text(self) -> None:
        # Skill is only mentioned in a highlight, not in the skills list.
        resume = self._resume(skills=[], summary="")
        report = compute_skill_match(["Python"], resume)
        assert report.matched_skills == ["python"]

    def test_legacy_description_field_is_searched(self) -> None:
        # Legacy resume payloads use `description` instead of `highlights`.
        resume = {
            "skills": [],
            "experience": [
                {
                    "company": "Old",
                    "title": "Engineer",
                    "description": "Worked extensively with Docker containers.",
                }
            ],
        }
        report = compute_skill_match(["Docker"], resume)
        assert "docker" in report.matched_skills

    def test_word_boundary_prevents_false_positives(self) -> None:
        # "java" must not match inside "javascript".
        resume = self._resume(skills=["JavaScript"], experience=[])
        report = compute_skill_match(["Java"], resume)
        assert "java" in report.missing_skills

    def test_dotted_skill_name_matched_correctly(self) -> None:
        resume = self._resume(skills=["Node.js", "Express"], experience=[])
        report = compute_skill_match(["Node.js"], resume)
        assert "node.js" in report.matched_skills

    def test_duplicate_required_skills_collapsed(self) -> None:
        # Same canonical skill listed twice (e.g. "React" + "ReactJS") only
        # contributes once to the totals.
        report = compute_skill_match(["React", "ReactJS"], self._resume(skills=["React"]))
        # Either matched once or missing once — never duplicated.
        total = len(report.matched_skills) + len(report.missing_skills)
        assert total == 1

    def test_report_to_dict_round_trip(self) -> None:
        report = compute_skill_match(["Python", "Rust"], self._resume())
        d = report_to_dict(report)
        assert set(d.keys()) == {"matched_skills", "missing_skills", "recall", "evidence"}
        assert d["recall"] == 0.5
        assert d["matched_skills"] == ["python"]
        assert d["missing_skills"] == ["rust"]

    def test_handles_missing_resume_fields_gracefully(self) -> None:
        # Empty / minimal resume should not crash.
        report = compute_skill_match(["Python"], {})
        assert report.matched_skills == []
        assert report.missing_skills == ["python"]
        assert report.recall == 0.0
