"""
End-to-end test suite for the RAG pipeline.

Hits the running API with structured test cases across four categories
(vague, red-flag, moderate, semantic) and validates the response
against expected behavior.

Usage (backend must be running on :8000):
    python -m backend.scripts.test_queries
    python -m backend.scripts.test_queries --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field

import requests

API_BASE = "http://localhost:8000"


# ── Test case definition ──

@dataclass
class TestCase:
    name: str
    category: str
    query: str
    expect_urgency: str
    expect_follow_ups: bool = False
    expect_no_conditions: bool = False
    expect_conditions: bool = False
    expect_sources: bool = False
    answer_must_contain: list[str] = field(default_factory=list)
    answer_must_not_contain: list[str] = field(default_factory=list)


@dataclass
class TestResult:
    name: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    response_time_ms: float = 0
    urgency: str = ""
    num_conditions: int = 0
    num_sources: int = 0
    answer_preview: str = ""


# ── Test cases ──

TESTS: list[TestCase] = [
    # ─── VAGUE QUERIES (should ask for clarification) ───
    TestCase(
        name="Vague: I don't feel well",
        category="vague",
        query="I don't feel well",
        expect_urgency="clarification_needed",
        expect_follow_ups=True,
        expect_no_conditions=True,
    ),
    TestCase(
        name="Vague: I feel sick",
        category="vague",
        query="I feel sick",
        expect_urgency="clarification_needed",
        expect_follow_ups=True,
        expect_no_conditions=True,
    ),
    TestCase(
        name="Vague: Something is wrong",
        category="vague",
        query="something is wrong with me",
        expect_urgency="clarification_needed",
        expect_follow_ups=True,
        expect_no_conditions=True,
    ),

    # ─── RED-FLAG QUERIES (should trigger emergency) ───
    TestCase(
        name="Red-flag: Chest pain and sweating",
        category="red_flag",
        query="I have chest pain and I'm sweating a lot",
        expect_urgency="emergency",
        expect_sources=True,
        answer_must_contain=["emergency", "medical"],
    ),
    TestCase(
        name="Red-flag: Can't breathe",
        category="red_flag",
        query="I can't breathe well and feel dizzy",
        expect_urgency="emergency",
        expect_sources=True,
        answer_must_contain=["emergency"],
    ),
    TestCase(
        name="Red-flag: Fainting and confusion",
        category="red_flag",
        query="I fainted and I feel confused",
        expect_urgency="emergency",
        expect_sources=True,
    ),

    # ─── MODERATE QUERIES (should retrieve + generate cautiously) ───
    TestCase(
        name="Moderate: Fever and cough",
        category="moderate",
        query="I have fever and cough for 3 days",
        expect_urgency="normal",
        expect_conditions=True,
        expect_sources=True,
    ),
    TestCase(
        name="Moderate: Headache and blurred vision",
        category="moderate",
        query="I have a persistent headache and blurred vision",
        expect_urgency="normal",
        expect_conditions=True,
        expect_sources=True,
    ),
    TestCase(
        name="Moderate: Nausea and vomiting",
        category="moderate",
        query="I've been having nausea and vomiting since yesterday",
        expect_urgency="normal",
        expect_sources=True,
    ),

    # ─── SEMANTIC QUERIES (informal language) ───
    TestCase(
        name="Semantic: My head hurts",
        category="semantic",
        query="my head hurts really bad",
        expect_urgency="normal",
        expect_sources=True,
    ),
    TestCase(
        name="Semantic: Feel like throwing up",
        category="semantic",
        query="I feel like I'm going to throw up and my stomach hurts",
        expect_urgency="normal",
        expect_sources=True,
    ),
    TestCase(
        name="Semantic: Tired all the time",
        category="semantic",
        query="I'm very tired all the time and have no energy",
        expect_urgency="normal",
        expect_sources=True,
    ),
]


# ── Runner ──

def _create_session() -> str:
    resp = requests.post(f"{API_BASE}/sessions", json={"title": "test-run"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["id"]


def _run_query(session_id: str, query: str) -> tuple[dict, float]:
    t0 = time.perf_counter()
    resp = requests.post(
        f"{API_BASE}/query",
        json={"session_id": session_id, "query": query},
        timeout=120,
    )
    elapsed = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    return resp.json(), elapsed


def _validate(tc: TestCase, data: dict) -> list[str]:
    """Return a list of failure messages (empty = pass)."""
    failures: list[str] = []

    urgency = data.get("urgency", "normal")
    if urgency != tc.expect_urgency:
        failures.append(f"urgency: expected '{tc.expect_urgency}', got '{urgency}'")

    follow_ups = data.get("follow_up_questions", [])
    if tc.expect_follow_ups and len(follow_ups) == 0:
        failures.append("expected follow-up questions but got none")

    conditions = data.get("related_topics", [])
    if tc.expect_no_conditions and len(conditions) > 0:
        names = [c["name"] for c in conditions]
        failures.append(f"expected NO conditions but got: {names}")

    if tc.expect_conditions and len(conditions) == 0:
        failures.append("expected related conditions but got none")

    sources = data.get("sources", [])
    if tc.expect_sources and len(sources) == 0:
        failures.append("expected sources but got none")

    answer = data.get("answer", "").lower()
    for keyword in tc.answer_must_contain:
        if keyword.lower() not in answer:
            failures.append(f"answer missing required keyword: '{keyword}'")

    for keyword in tc.answer_must_not_contain:
        if keyword.lower() in answer:
            failures.append(f"answer contains forbidden keyword: '{keyword}'")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the RAG pipeline")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("Medical Symptom Assistant — Pipeline Test Suite")
    print(f"{'=' * 60}")

    try:
        session_id = _create_session()
    except Exception as e:
        print(f"\nFATAL: Cannot connect to backend at {API_BASE}")
        print(f"       {e}")
        print("       Is the backend running?  (uvicorn backend.main:app --reload)")
        sys.exit(1)

    results: list[TestResult] = []
    categories: dict[str, list[TestResult]] = {}

    for i, tc in enumerate(TESTS, 1):
        print(f"\n[{i}/{len(TESTS)}] {tc.name}")
        print(f"     Query: {tc.query!r}")

        try:
            # Each test gets its own session to avoid history interference
            sid = _create_session()
            data, elapsed = _run_query(sid, tc.query)
            failures = _validate(tc, data)

            res = TestResult(
                name=tc.name,
                passed=len(failures) == 0,
                failures=failures,
                response_time_ms=elapsed,
                urgency=data.get("urgency", "?"),
                num_conditions=len(data.get("related_topics", [])),
                num_sources=len(data.get("sources", [])),
                answer_preview=data.get("answer", "")[:120],
            )

            status = "PASS" if res.passed else "FAIL"
            print(f"     {status}  (urgency={res.urgency}, "
                  f"conditions={res.num_conditions}, "
                  f"sources={res.num_sources}, "
                  f"{res.response_time_ms:.0f} ms)")

            if not res.passed:
                for f in failures:
                    print(f"       ✗ {f}")

            if args.verbose:
                print(f"     Answer: {res.answer_preview}…")
                if data.get("follow_up_questions"):
                    print(f"     Follow-ups: {data['follow_up_questions']}")

        except Exception as e:
            res = TestResult(name=tc.name, passed=False, failures=[str(e)])
            print(f"     ERROR: {e}")

        results.append(res)
        categories.setdefault(tc.category, []).append(res)

    # ── Summary ──
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_ms = sum(r.response_time_ms for r in results) / len(results) if results else 0

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{len(results)} passed, {failed} failed")
    print(f"Average response time: {avg_ms:.0f} ms")
    print()

    for cat, cat_results in categories.items():
        cat_passed = sum(1 for r in cat_results if r.passed)
        cat_label = f"{cat_passed}/{len(cat_results)}"
        indicator = "ALL PASS" if cat_passed == len(cat_results) else "HAS FAILURES"
        print(f"  {cat:15s}  {cat_label}  {indicator}")

    print(f"{'=' * 60}\n")

    if failed > 0:
        print("FAILED TESTS:")
        for r in results:
            if not r.passed:
                print(f"  • {r.name}")
                for f in r.failures:
                    print(f"      ✗ {f}")
        print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
