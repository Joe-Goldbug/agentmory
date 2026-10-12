"""Retire obsolete automatic analysis plans without deleting source evidence."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from lwm.memory_compiler import ANALYSIS_DIR, load_candidate, record_transition, save_candidate
from lwm.structured_candidates import TRANSPORT_TAGS, generic_observation


def compact_analysis_queue(root: Path) -> dict:
    """Caller owns the cycle lock; human-reviewed records remain untouched."""
    candidates = {p.stem: c for p in sorted((root / ANALYSIS_DIR).glob("*.json"))
                  if (c := load_candidate(root, p.stem)) is not None}
    roots = {k: c for k, c in candidates.items() if not c.analysis_parent_id}
    protected = set()
    review = {}
    for key, candidate in roots.items():
        path = root / "state/candidates" / f"{key}.json"
        try:
            payload = json.loads(path.read_text()) if path.exists() else {}
        except (OSError, ValueError):
            protected.add(key)
            continue
        if not isinstance(payload, dict):
            protected.add(key)
            continue
        review[key] = payload
        if (candidate.state not in {"pending_analysis", "retry_wait"}
                or payload.get("state") in {"accepted", "corrected", "rejected"}
                or payload.get("correction") or "User correction:" in candidate.context):
            protected.add(key)
    plans = {}
    seen = {}
    for key, candidate in roots.items():
        if key in protected:
            continue
        metadata = any(candidate.claim == f"The `{tag}` pattern may connect these projects"
                       for tag in TRANSPORT_TAGS)
        topic = str(review.get(key, {}).get("semantic_topic") or "")
        observation = topic.startswith("task:") and generic_observation(topic[5:])
        if metadata or observation:
            plans[key] = {"reason": "metadata_relationship" if metadata else "generic_observation",
                          "replacement_id": None}
            continue
        fields = ("kind", "claim", "scope", "evidence_ids", "counterevidence_ids", "context", "uncertainty", "validity")
        payload = candidate.to_dict()
        identity = {f: sorted(payload[f]) if isinstance(payload[f], (tuple, list)) else payload[f]
                    for f in fields}
        signature = json.dumps(identity, sort_keys=True, ensure_ascii=False)
        if signature in seen:
            plans[key] = {"reason": "identical_semantic_request", "replacement_id": seen[signature]}
        else:
            seen[signature] = key
    path = root / "state/analysis/compaction.json"
    existing = json.loads(path.read_text()) if path.exists() else {"version": 1, "retired": {}}
    retired = []
    # Retire children first so an interrupted migration can resume from its
    # still-pending root without stranding active descendants.
    for key, candidate in sorted(candidates.items(), key=lambda pair: (not bool(pair[1].analysis_parent_id), pair[0])):
        owner = candidate.analysis_parent_id or key
        if owner not in plans or candidate.state not in {"pending_analysis", "retry_wait"}:
            continue
        detail = {**plans[owner], "root_id": owner,
                  "evidence_ids": sorted(set(candidate.evidence_ids) | set(candidate.counterevidence_ids)),
                  "prior_state": candidate.state}
        # Persist the recovery mapping before changing candidate state.
        existing["retired"][key] = detail
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)
        record_transition(root, key, from_state=candidate.state, to_state="retired",
                          note=f"queue compaction: {detail['reason']}")
        save_candidate(root, replace(candidate, state="retired"))
        retired.append(key)
    return {"retired": retired, "protected_roots": sorted(protected)}
