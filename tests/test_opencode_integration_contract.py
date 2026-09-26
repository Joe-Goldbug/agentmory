"""The checked-in OpenCode plugin must use the shared bridge contract."""

from pathlib import Path


PLUGIN = Path(__file__).parents[1] / "integrations" / "opencode" / "lwm-workmem.ts"
LEGACY_SHELL_ADAPTER = Path(__file__).parents[1] / "adapters" / "lwm-shell-context.sh"


def test_opencode_plugin_uses_bridge_for_context_and_lifecycle() -> None:
    text = PLUGIN.read_text(encoding="utf-8")

    assert "hub bridge" in text
    assert 'phase: "context"' in text
    assert 'phase,' in text
    assert 'integration: "opencode-plugin"' in text
    assert "LWM_HOST_BRIDGE=1" in text
    assert "process.env.LWM_ROOT" in text
    assert "process.env.LWM_BIN" in text
    assert "Mobile Documents" not in text
    assert "/Users/ethan/" not in text
    assert "hub context" not in text
    assert "hub lifecycle" not in text


def test_legacy_shell_adapter_also_uses_shared_bridge() -> None:
    text = LEGACY_SHELL_ADAPTER.read_text(encoding="utf-8")

    assert "hub bridge" in text
    assert '"tool":"shell"' in text
    assert "sed -n" not in text


def test_generated_opencode_plugin_does_not_embed_installer_checkout(tmp_path: Path) -> None:
    from lwm.hooks_gen import _opencode_plugin

    text = _opencode_plugin(tmp_path / "source checkout")

    assert str(tmp_path) not in text
    assert "process.env.LWM_ROOT" in text
    assert "process.env.LWM_BIN" in text
    assert "node:os" in text
    assert "LWM_HOST_BRIDGE=1" in text


def test_generated_opencode_plugin_delivers_context_and_captures_bounded_activity(
    tmp_path: Path,
) -> None:
    from lwm.hooks_gen import _opencode_plugin

    text = _opencode_plugin(tmp_path / "source checkout")

    assert '"experimental.chat.system.transform"' in text
    assert '"chat.message"' in text
    assert 'event_type: "session_summary"' in text
    assert "lastPromptBySession" in text
    assert "parts" in text
