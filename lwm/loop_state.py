"""Deterministic control state for one bounded LLM-WorkMem loop."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXIT_STATES = {"continue", "completed_verified", "human_required", "blocked"}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class LoopState:
    loop_id: str
    objective: str
    constraints: tuple[str, ...]
    success_criteria: tuple[str, ...]
    phase: str
    expected_observation: str
    expected_outcome: str
    actual_observation: str
    actual_outcome: str
    evidence: tuple[str, ...]
    criteria_met: bool | None
    attempt: int
    next_action: str
    exit_state: str
    human_gate: bool
    started_at: str
    finished_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "constraints": list(self.constraints),
            "success_criteria": list(self.success_criteria),
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoopState":
        return cls(
            loop_id=str(payload.get("loop_id", "")),
            objective=str(payload.get("objective", "")),
            constraints=tuple(str(item) for item in payload.get("constraints", [])),
            success_criteria=tuple(str(item) for item in payload.get("success_criteria", [])),
            phase=str(payload.get("phase", "observe")),
            expected_observation=str(payload.get("expected_observation", "")),
            expected_outcome=str(payload.get("expected_outcome", "")),
            actual_observation=str(payload.get("actual_observation", "")),
            actual_outcome=str(payload.get("actual_outcome", "")),
            evidence=tuple(str(item) for item in payload.get("evidence", [])),
            criteria_met=payload.get("criteria_met"),
            attempt=int(payload.get("attempt", 1)),
            next_action=str(payload.get("next_action", "")),
            exit_state=str(payload.get("exit_state", "continue")),
            human_gate=bool(payload.get("human_gate", False)),
            started_at=str(payload.get("started_at", "")),
            finished_at=payload.get("finished_at"),
        )


def begin_loop(
    objective: str,
    *,
    constraints: tuple[str, ...] = (),
    success_criteria: tuple[str, ...] = (),
    expected_observation: str = "",
    expected_outcome: str = "",
    attempt: int = 1,
) -> LoopState:
    return LoopState(
        loop_id=str(uuid.uuid4()),
        objective=objective,
        constraints=tuple(constraints),
        success_criteria=tuple(success_criteria),
        phase="observe",
        expected_observation=expected_observation,
        expected_outcome=expected_outcome,
        actual_observation="",
        actual_outcome="",
        evidence=(),
        criteria_met=None,
        attempt=attempt,
        next_action="",
        exit_state="continue",
        human_gate=False,
        started_at=_now(),
        finished_at=None,
    )


def record_evaluation(
    state: LoopState,
    *,
    actual_observation: str,
    actual_outcome: str,
    evidence: tuple[str, ...],
    criteria_met: bool,
    next_action: str,
) -> LoopState:
    return replace(
        state,
        phase="update" if criteria_met else "decompose",
        actual_observation=actual_observation,
        actual_outcome=actual_outcome,
        evidence=tuple(evidence),
        criteria_met=criteria_met,
        next_action=next_action,
        exit_state="continue",
        human_gate=False,
        finished_at=None,
    )


def close_loop(state: LoopState, *, exit_state: str, human_gate: bool) -> LoopState:
    if exit_state not in EXIT_STATES:
        raise ValueError(f"unsupported loop exit state: {exit_state}")
    if exit_state == "completed_verified" and (state.criteria_met is not True or not state.evidence):
        return replace(
            state,
            phase="decompose",
            exit_state="continue",
            human_gate=False,
            finished_at=None,
        )
    terminal = exit_state != "continue"
    return replace(
        state,
        phase="update" if terminal else state.phase,
        exit_state=exit_state,
        human_gate=human_gate,
        finished_at=_now() if terminal else None,
    )


def _path(root: Path, name: str) -> Path:
    return root / "state" / name


def write_state(root: Path, state: LoopState) -> Path:
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = _path(root, "active-loop.json" if state.exit_state == "continue" else "last-loop.json")
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    if state.exit_state != "continue":
        _path(root, "active-loop.json").unlink(missing_ok=True)
    return target


def _read(root: Path, name: str) -> LoopState | None:
    path = _path(root, name)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return LoopState.from_dict(payload) if isinstance(payload, dict) else None


def read_active(root: Path) -> LoopState | None:
    return _read(root, "active-loop.json")


def read_last(root: Path) -> LoopState | None:
    return _read(root, "last-loop.json")


__all__ = [
    "EXIT_STATES",
    "LoopState",
    "begin_loop",
    "close_loop",
    "read_active",
    "read_last",
    "record_evaluation",
    "write_state",
]
