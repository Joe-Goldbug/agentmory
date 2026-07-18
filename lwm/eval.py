"""Lightweight, reproducible query evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import fnmatch

from lwm.recall import RecallPacket, build_recall_packet
from lwm.query import run_query


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_slug: str
    expected_fact: str | None = None
    expected_project: str | None = None
    expected_coverage: str | None = None
    expect_conflict: bool = False


@dataclass(frozen=True)
class EvalResult:
    case: EvalCase
    top_slug: str
    passed: bool


@dataclass(frozen=True)
class RecallEvalResult:
    case: EvalCase
    packet: RecallPacket
    fact_match: bool
    project_match: bool
    coverage_match: bool
    conflict_match: bool

    @property
    def passed(self) -> bool:
        return all(
            (self.fact_match, self.project_match, self.coverage_match, self.conflict_match)
        )


@dataclass(frozen=True)
class RecallEvalReport:
    root: Path
    results: tuple[RecallEvalResult, ...]

    @property
    def pass_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def total(self) -> int:
        return len(self.results)


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
        fields = [part.strip() for part in line.split("|")]
        question, expected = fields[0], fields[1]
        if question and expected:
            cases.append(
                EvalCase(
                    question=question,
                    expected_slug=expected.lower(),
                    expected_fact=fields[2] or None if len(fields) > 2 else None,
                    expected_project=fields[3] or None if len(fields) > 3 else None,
                    expected_coverage=fields[4] or None if len(fields) > 4 else None,
                    expect_conflict=(fields[5].lower() == "true") if len(fields) > 5 else False,
                )
            )
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


def run_recall_eval(
    root: Path,
    suite_path: Path,
    *,
    project_path: str | None = None,
    now: datetime | str | None = None,
    limit: int = 6,
) -> RecallEvalReport:
    """Evaluate source-backed packets without calling an external model."""

    cases = parse_eval_suite(suite_path)
    results: list[RecallEvalResult] = []
    for case in cases:
        packet = build_recall_packet(
            root,
            case.question,
            project_path=project_path,
            now=now,
            limit=limit,
        )
        statements = " ".join(item.statement.lower() for item in packet.evidence)
        fact_match = not case.expected_fact or case.expected_fact.lower() in statements
        project_match = not case.expected_project or packet.project_id == case.expected_project
        coverage_match = not case.expected_coverage or packet.coverage == case.expected_coverage
        conflict_match = bool(packet.conflicts) == case.expect_conflict
        results.append(
            RecallEvalResult(
                case=case,
                packet=packet,
                fact_match=fact_match,
                project_match=project_match,
                coverage_match=coverage_match,
                conflict_match=conflict_match,
            )
        )
    return RecallEvalReport(root=root.resolve(), results=tuple(results))


def render_recall_eval_report(report: RecallEvalReport) -> str:
    lines = [
        f"# Recall Eval Report — {report.root.name}",
        "",
        f"- Passed: {report.pass_count}/{report.total}",
        "",
        "## Cases",
    ]
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"- {status} | {result.case.question} | fact={result.fact_match} "
            f"project={result.project_match} coverage={result.coverage_match} "
            f"conflict={result.conflict_match}"
        )
    return "\n".join(lines)
