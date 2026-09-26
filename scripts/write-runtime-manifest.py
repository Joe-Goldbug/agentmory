#!/usr/bin/env python3
"""Write a machine-readable runtime manifest from hash command output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def parse_hash_lines(lines: list[str]) -> list[str]:
    entries: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        digest, separator, path = line.partition("  ")
        if not separator or not _SHA256_RE.fullmatch(digest) or not path:
            raise ValueError(f"invalid manifest hash line: {line!r}")
        entries.append(f"{digest.lower()}  {path}")
    return entries


def write_manifest(
    output: Path,
    *,
    runtime_id: str,
    source_revision: str,
    source_dirty_hash: str,
    source_root: str,
    runtime_root: str,
    python: str,
    wheel: str,
    import_probe: str,
    hash_lines: list[str],
) -> None:
    try:
        probe = json.loads(import_probe)
    except json.JSONDecodeError as exc:
        raise ValueError("import probe must be valid JSON") from exc
    if not isinstance(probe, dict):
        raise ValueError("import probe must be a JSON object")

    payload = {
        "runtime_id": runtime_id,
        "source_revision": source_revision,
        "source_dirty_hash": source_dirty_hash,
        "source_root": source_root,
        "runtime_root": runtime_root,
        "python": python,
        "editable": False,
        "wheel": wheel,
        "import_probe": probe,
        "file_hashes": parse_hash_lines(hash_lines),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "runtime-id",
        "source-revision",
        "source-dirty-hash",
        "source-root",
        "runtime-root",
        "python",
        "wheel",
        "import-probe",
    ):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        write_manifest(
            args.output,
            runtime_id=args.runtime_id,
            source_revision=args.source_revision,
            source_dirty_hash=args.source_dirty_hash,
            source_root=args.source_root,
            runtime_root=args.runtime_root,
            python=args.python,
            wheel=args.wheel,
            import_probe=args.import_probe,
            hash_lines=sys.stdin.readlines(),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
