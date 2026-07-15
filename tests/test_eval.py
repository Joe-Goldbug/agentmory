from lwm.eval import matches_expected_slug


def test_eval_accepts_stable_wildcard_for_dated_page() -> None:
    assert matches_expected_slug("tool-harvest-2026-07-12", "tool-harvest-*")
    assert not matches_expected_slug("memory-governance", "tool-harvest-*")
