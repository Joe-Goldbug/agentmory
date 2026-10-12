"""Live retrieval smoke checks and opt-in source-backed recall contracts.

Product acceptance runs isolated deterministic fixtures in
``tests/test_memory_e2e_repair.py``, not private fixtures in a user's live wiki.
Neither report proves actual IDE delivery or production operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files as resource_files
from pathlib import Path
import fnmatch
import json

from lwm.recall import RecallPacket, build_recall_packet
from lwm.query import run_query


def packaged_eval_suite():
    """Return the authoritative eval suite bundled with the installed wheel."""

    return resource_files("lwm.resources").joinpath("eval-suite.txt")


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_slug: str
    expected_fact: str | None = None
    expected_project: str | None = None
    expected_coverage: str | None = None
    expect_conflict: bool = False
    expected_source: str | None = None
    forbidden_fact: str | None = None
    expected_verification: str | None = None


@dataclass(frozen=True)
class EvalResult:
    case: EvalCase
    top_slug: str
    passed: bool
    recall_result: RecallEvalResult | None = None


@dataclass(frozen=True)
class RecallEvalResult:
    case: EvalCase
    packet: RecallPacket
    fact_match: bool
    project_match: bool
    coverage_match: bool
    conflict_match: bool
    source_match: bool = True
    absence_match: bool = True
    verification_match: bool = True

    @property
    def passed(self) -> bool:
        return all(
            (
                self.fact_match,
                self.project_match,
                self.coverage_match,
                self.conflict_match,
                self.source_match,
                self.absence_match,
                self.verification_match,
            )
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
    return fnmatch.fnmatchcase(actual.replace("\\", "/"), expected.replace("\\", "/"))


def parse_eval_suite(path) -> tuple[EvalCase, ...]:
    cases: list[EvalCase] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            continue
        fields = [part.strip() for part in line.split("|")]
        if len(fields) > 9:
            raise ValueError("Eval cases support at most nine fields")
        if len(fields) > 5 and fields[5].lower() not in {"", "true", "false"}:
            raise ValueError("expect_conflict must be true or false")
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
                    expected_source=fields[6] or None if len(fields) > 6 else None,
                    forbidden_fact=fields[7] or None if len(fields) > 7 else None,
                    expected_verification=fields[8] or None if len(fields) > 8 else None,
                )
            )
    return tuple(cases)


def run_eval(
    root: Path,
    suite_path,
    *,
    mode: str = "standard",
    limit: int = 3,
    project_path: str | None = None,
    now: datetime | str | None = None,
) -> EvalReport:
    root = root.resolve()
    suite = parse_eval_suite(suite_path)
    results: list[EvalResult] = []
    for case in suite:
        report = run_query(root, case.question, mode=mode, limit=limit)
        # Generated views are useful to readers, but they are not the stable
        # durable page targeted by these slug-based regression cases.
        durable_hits = tuple(
            hit
            for hit in report.hits
            if hit.page.page_type not in {"insight", "review", "unified-memory"}
        )
        explicit_view = next(
            (
                hit
                for hit in report.hits
                if hit.page.page_type == "unified-memory"
                and matches_expected_slug(hit.page.slug, case.expected_slug)
            ),
            None,
        )
        top_hit = explicit_view or (
            durable_hits[0] if durable_hits else (report.hits[0] if report.hits else None)
        )
        top_slug = top_hit.page.slug if top_hit else ""
        # Generated pages commonly include a date suffix. Allow eval suites
        # to express that contract without expiring every morning.
        passed = matches_expected_slug(top_slug, case.expected_slug)
        recall_result = None
        if any(
            (
                case.expected_fact,
                case.expected_project,
                case.expected_coverage,
                case.expect_conflict,
                case.expected_source,
                case.forbidden_fact,
                case.expected_verification,
            )
        ):
            packet = build_recall_packet(
                root, case.question, project_path=project_path, now=now, limit=limit
            )
            recall_result = _evaluate_recall_case(case, packet)
            passed = passed and recall_result.passed
        results.append(
            EvalResult(
                case=case,
                top_slug=top_slug,
                passed=passed,
                recall_result=recall_result,
            )
        )
    return EvalReport(root=root, mode=mode, results=tuple(results))


def render_eval_report(report: EvalReport) -> str:
    lines = [
        f"# Eval Report — {report.root.name}",
        "",
        f"- Mode: {report.mode}",
        f"- Passed: {report.pass_count}/{report.total}",
        "- Scope: retrieval regression, not product acceptance or actual IDE delivery.",
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
        if result.recall_result is not None:
            lines.append(f"  Source-backed contract: {_recall_checks(result.recall_result)}")
    return "\n".join(lines)


def _evaluate_recall_case(case: EvalCase, packet: RecallPacket) -> RecallEvalResult:
    # Historical/conflicted text is visible counterevidence, not current support.
    current = tuple(item for item in packet.evidence if item.state == "current")
    supporting = tuple(
        item
        for item in current
        if not case.expected_fact or case.expected_fact.lower() in item.statement.lower()
    )
    project_match = not case.expected_project or (
        packet.project_id == case.expected_project
        and all(
            item.project_id == case.expected_project
            for item in (*packet.evidence, *packet.conflicts)
        )
    )
    source_support = tuple(
        item
        for item in supporting
        if not case.expected_source
        or any(matches_expected_slug(path, case.expected_source) for path in item.source_paths)
    )
    source_match = not case.expected_source or bool(source_support)
    verification_match = not case.expected_verification or any(
        case.expected_verification.lower() in verification.lower()
        for item in source_support
        for verification in item.verification
    )
    visible = json.dumps(packet.as_dict(), ensure_ascii=False)
    absence_match = not case.forbidden_fact or case.forbidden_fact.lower() not in visible.lower()
    return RecallEvalResult(
        case=case,
        packet=packet,
        fact_match=not case.expected_fact or bool(supporting),
        project_match=project_match,
        coverage_match=not case.expected_coverage or packet.coverage == case.expected_coverage,
        conflict_match=bool(packet.conflicts) == case.expect_conflict,
        source_match=source_match,
        absence_match=absence_match,
        verification_match=verification_match,
    )


def _recall_checks(result: RecallEvalResult) -> str:
    return (
        f"fact={result.fact_match} project={result.project_match} "
        f"coverage={result.coverage_match} conflict={result.conflict_match} "
        f"source={result.source_match} absence={result.absence_match} "
        f"verification={result.verification_match}"
    )


def run_recall_eval(
    root: Path,
    suite_path,
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
        results.append(_evaluate_recall_case(case, packet))
    return RecallEvalReport(root=root.resolve(), results=tuple(results))


def render_recall_eval_report(report: RecallEvalReport) -> str:
    lines = [
        f"# Recall Eval Report — {report.root.name}",
        "",
        f"- Passed: {report.pass_count}/{report.total}",
        "- Scope: source-backed recall regression, not product acceptance or actual IDE delivery.",
        "",
        "## Cases",
    ]
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"- {status} | {result.case.question} | {_recall_checks(result)}")
    return "\n".join(lines)
