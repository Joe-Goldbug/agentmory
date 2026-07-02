"""Canonical wiki directory layout (INIT). Kept in sync with the wiki skill SKILL.md."""

from __future__ import annotations

from lwm.profiles import DEFAULT_PROFILE, render_profile_tree, render_structure_text as _render_structure_text


def render_structure_text(profile: str = DEFAULT_PROFILE) -> str:
    """Full text for `lwm structure` (tree + required commands)."""
    return _render_structure_text(profile)


def render_structure_compact(profile: str = DEFAULT_PROFILE) -> str:
    """Tree only (for tests or embedding)."""
    return render_profile_tree(profile)
