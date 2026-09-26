from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import lwm.memory_federation as federation
from lwm.memory_federation import (
    CLAIMS_PATH,
    RELEASE_PATH,
    compile_federated_memory,
    load_published_memory,
    restore_federated_release,
)


def _snapshot(root: Path, tool: str, name: str, body: str) -> None:
    target = root / "raw" / "tool-snapshots" / tool / "current" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def test_federation_prefers_opencode_and_publishes_one_current_view(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: use concise Chinese output\n")
    _snapshot(tmp_path, "codex", "memory.md", "- Workflow: use concise Chinese output\n")

    report = compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)

    assert report["status"] == "ok"
    assert published["claims"][0]["tool"] == "opencode"
    assert published["conflicts"] == []
    assert (tmp_path / "wiki/unified/workflow-memory.md").is_file()


def test_federation_does_not_resolve_unverified_disagreement_by_tool(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Model choice: use MiniMax for local speed\n")
    _snapshot(tmp_path, "codex", "memory.md", "- Model choice: use OpenAI for local speed\n")

    compile_federated_memory(tmp_path)
    records = json.loads((tmp_path / CLAIMS_PATH).read_text(encoding="utf-8"))["claims"]

    assert all(row["status"] == "conflicted" for row in records)


def test_generic_status_from_distinct_projects_is_not_a_conflict(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "project-a.md", "- Status: Project A is ready to launch\n")
    _snapshot(tmp_path, "codex", "project-b.md", "- Status: Project B is still in design\n")

    compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)

    assert len(published["claims"]) == 2
    assert {row["tool"] for row in published["claims"]} == {"opencode", "codex"}
    assert published["conflicts"] == []


def test_verified_new_fact_beats_tool_priority(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Model choice: use MiniMax for local speed\n")
    _snapshot(tmp_path, "codex", "memory.md", "- Model choice: use OpenAI for local speed [verified: 2026-09-24]\n")

    compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)

    assert len(published["claims"]) == 1
    assert published["claims"][0]["tool"] == "codex"
    assert "[verified" not in published["claims"][0]["statement"]


def test_rollout_metadata_and_similar_distinct_facts_are_not_claims_or_conflicts(tmp_path: Path) -> None:
    _snapshot(tmp_path, "codex", "memory.md", """### rollout_summary_files
- rollout_summaries/example.md (cwd=/tmp, rollout_path=/tmp/example.jsonl, updated_at=2026-09-24)
### keywords
- MiniMax, OpenAI, model choice
## Reusable knowledge
- Model choice: use OpenAI for local speed
- Model choice: use OpenAI for remote quality
""")
    _snapshot(tmp_path, "opencode", "memory.md", "- Model choice: use OpenAI for local speed\n")

    compile_federated_memory(tmp_path)
    published = load_published_memory(tmp_path)

    assert len(published["claims"]) == 2
    assert published["conflicts"] == []
    assert all("rollout_path" not in row["statement"] for row in published["claims"])


def test_old_snapshot_is_not_published_as_current(tmp_path: Path) -> None:
    _snapshot(tmp_path, "codex", "memory.md", "- Workflow: retain verified decisions\n")
    path = tmp_path / "raw/tool-snapshots/codex/current/memory.md"
    old = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(path, (old, old))

    report = compile_federated_memory(tmp_path)

    assert report["stale"] == 1
    assert load_published_memory(tmp_path)["claims"] == []


def test_loader_uses_only_complete_pointer_release(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release one\n")
    first = compile_federated_memory(tmp_path)
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release two\n")
    second = compile_federated_memory(tmp_path)
    pointer = tmp_path / RELEASE_PATH
    pointer.write_text(json.dumps({"release_id": first["release_id"], "path": f"state/federation/releases/{first['release_id']}.json"}), encoding="utf-8")

    published = load_published_memory(tmp_path)

    assert published["release_id"] == first["release_id"]
    assert "release one" in published["claims"][0]["statement"]
    assert second["release_id"] != first["release_id"]


def test_loader_rejects_missing_or_mismatched_pointer_release(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release one\n")
    compile_federated_memory(tmp_path)
    pointer = tmp_path / RELEASE_PATH
    pointer.write_text(json.dumps({"release_id": "wrong", "path": "state/federation/claims.json"}), encoding="utf-8")

    assert load_published_memory(tmp_path)["claims"] == []


def test_failed_publish_keeps_previous_pointer_visible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release one\n")
    first = compile_federated_memory(tmp_path)
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release two\n")
    real_write = federation._safe_text_write

    def fail_legacy_page(path: Path, content: str) -> None:
        if path == tmp_path / federation.UNIFIED_PAGE:
            raise OSError("simulated page write failure")
        real_write(path, content)

    monkeypatch.setattr(federation, "_safe_text_write", fail_legacy_page)
    with pytest.raises(OSError, match="simulated"):
        compile_federated_memory(tmp_path)

    published = load_published_memory(tmp_path)
    assert published["release_id"] == first["release_id"]
    assert "release one" in published["claims"][0]["statement"]


def test_federation_archives_claim_missing_from_current_source(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: retain verified decisions\n")
    compile_federated_memory(tmp_path)
    (tmp_path / "raw/tool-snapshots/opencode/current/memory.md").write_text(
        "- Workflow: retain only current decisions\n", encoding="utf-8"
    )

    report = compile_federated_memory(tmp_path)
    records = json.loads((tmp_path / CLAIMS_PATH).read_text(encoding="utf-8"))["claims"]

    assert report["archived"] == 1
    assert any(row["status"] == "archived" for row in records)


def test_federation_release_can_be_restored(tmp_path: Path) -> None:
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release one\n")
    first = compile_federated_memory(tmp_path)
    _snapshot(tmp_path, "opencode", "memory.md", "- Workflow: keep release two\n")
    compile_federated_memory(tmp_path)

    restored = restore_federated_release(tmp_path, first["release_id"])

    assert restored["release_id"] == first["release_id"]
    assert "release one" in (tmp_path / "wiki/unified/workflow-memory.md").read_text(encoding="utf-8")
