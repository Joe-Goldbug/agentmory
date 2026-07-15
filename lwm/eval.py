"""Lightweight, reproducible query evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import fnmatch

from lwm.query import run_query


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_slug: str


@dataclass(frozen=True)
class EvalResult:
    case: EvalCase
    top_slug: str
    passed: bool


@dataclass(frozen=True)
class EvalReport:
    root: Path
    mode: str
    results: tuple[EvalResult, ...]

    @property
    def pass_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def total(self) -> int:
        return len(self.results)


def matches_expected_slug(actual: str, expected: str) -> bool:
    """Match exact slugs and stable glob contracts such as ``tool-harvest-*``."""
    return fnmatch.fnmatchcase(actual, expected)


def parse_eval_suite(path: Path) -> tuple[EvalCase, ...]:
    cases: list[EvalCase] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            continue
        question, expected = [part.strip() for part in line.split("|", 1)]
        if question and expected:
            cases.append(EvalCase(question=question, expected_slug=expected.lower()))
    return tuple(cases)


def run_eval(root: Path, suite_path: Path, *, mode: str = "standard", limit: int = 3) -> EvalReport:
    root = root.resolve()
    suite = parse_eval_suite(suite_path)
    results: list[EvalResult] = []
    for case in suite:
        report = run_query(root, case.question, mode=mode, limit=limit)
        top_slug = report.hits[0].page.slug if report.hits else ""
        # Generated pages commonly include a date suffix. Allow eval suites
        # to express that contract without expiring every morning.
        passed = matches_expected_slug(top_slug, case.expected_slug)
        results.append(
            EvalResult(
                case=case,
                top_slug=top_slug,
                passed=passed,
            )
        )
    return EvalReport(root=root, mode=mode, results=tuple(results))


def render_eval_report(report: EvalReport) -> str:
    lines = [
        f"# Eval Report — {report.root.name}",
        "",
        f"- Mode: {report.mode}",
        f"- Passed: {report.pass_count}/{report.total}",
        "",
        "## Cases",
    ]
    if not report.results:
        lines.append("- No cases found in eval suite.")
        return "\n".join(lines)
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"- {status} | q: {result.case.question} | expected: {result.case.expected_slug} | got: {result.top_slug or '_none_'}"
        )
    return "\n".join(lines)
