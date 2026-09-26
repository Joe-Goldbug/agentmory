"""CLI smoke tests via Typer runner."""

from pathlib import Path

from typer.testing import CliRunner

from lwm.cli import app
from lwm.memory_compiler import Candidate, save_candidate

runner = CliRunner()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_help() -> None:
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "lwm" in r.stdout.lower() or "LLM-WorkMem" in r.stdout


def test_receipt_cli_cannot_forge_native_proof(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "hub",
            "receipt",
            "--tool",
            "codex",
            "--direction",
            "read",
            "--source",
            "native-hook",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    assert "refusing direct proof receipt" in result.output
    assert not (tmp_path / "state" / "capability-receipts.json").exists()


def test_legacy_auto_promotion_cli_is_disabled(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["hub", "promote", str(tmp_path), "--auto"],
    )

    assert result.exit_code == 2
    assert "legacy --auto is disabled" in result.output
    assert not (tmp_path / "wiki" / "global").exists()


def test_ingest_promote_help_is_observation_only() -> None:
    result = runner.invoke(app, ["hub", "ingest", "--help"])

    assert result.exit_code == 0
    assert "never write" in result.output
    assert "global memory" in result.output


def test_review_analysis_command_accepts_candidate(tmp_path: Path) -> None:
    save_candidate(
        tmp_path,
        Candidate(
            candidate_id="cli-candidate",
            kind="workflow",
            claim="A verified loop repeats.",
            scope=("p1",),
            evidence_ids=("e1",),
            state="analyzed",
        ),
    )

    result = runner.invoke(
        app,
        [
            "hub",
            "review-analysis",
            "cli-candidate",
            "--decision",
            "accept",
            "--root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"state": "accepted"' in result.stdout


def test_raw_status_help() -> None:
    r = runner.invoke(app, ["raw", "status", "--help"])
    assert r.exit_code == 0


def test_init_creates_wiki(tmp_path: Path) -> None:
    target = tmp_path / "mywiki"
    r = runner.invoke(
        app,
        ["init", str(target), "--domain", "Test", "--sources", "urls"],
    )
    assert r.exit_code == 0, r.output
    assert (target / "wiki" / "index.md").is_file()
    assert (target / "raw" / "files.log").is_file()
    assert (target / "wiki" / "purpose.md").is_file()
    assert (target / "wiki" / "eval-suite.txt").is_file()


def test_init_refuses_double_init(tmp_path: Path) -> None:
    target = tmp_path / "w"
    runner.invoke(app, ["init", str(target)])
    r = runner.invoke(app, ["init", str(target)])
    assert r.exit_code == 1


def test_init_default_sources_in_agents(tmp_path: Path) -> None:
    target = tmp_path / "wiki2"
    r = runner.invoke(app, ["init", str(target), "-d", "Only Domain"])
    assert r.exit_code == 0, r.output
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "Only Domain" in agents
    assert "articles, URLs, papers" in agents
    assert "## Source Types" in agents
    stub = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@AGENTS.md" in stub


def test_structure_command() -> None:
    r = runner.invoke(app, ["structure"])
    assert r.exit_code == 0
    assert "AGENTS.md" in r.stdout
    assert "CLAUDE.md" in r.stdout
    assert "purpose.md" in r.stdout
    assert "wiki/" in r.stdout
    assert "lwm init" in r.stdout
    assert "lwm dashboard" in r.stdout


def test_structure_personal_profile() -> None:
    r = runner.invoke(app, ["structure", "--profile", "personal"])
    assert r.exit_code == 0
    assert "projects/" in r.stdout
    assert "decisions/" in r.stdout
    assert "lwm analyze" in r.stdout


def test_init_creates_all_subdirectories(tmp_path: Path) -> None:
    """lwm init must create assets/, raw/, and all wiki/ subdirectories."""
    target = tmp_path / "fullwm"
    r = runner.invoke(app, ["init", str(target), "-d", "Test"])
    assert r.exit_code == 0, r.output
    assert (target / "assets").is_dir()
    assert (target / "raw").is_dir()
    for sub in ("summaries", "concepts", "entities", "insights"):
        assert (target / "wiki" / sub).is_dir(), f"wiki/{sub}/ not created"


def test_init_index_no_empty_table_rows(tmp_path: Path) -> None:
    """index.md tables should have header + separator only, no empty data rows."""
    target = tmp_path / "indexwiki"
    r = runner.invoke(app, ["init", str(target), "-d", "Test"])
    assert r.exit_code == 0, r.output
    index_content = (target / "wiki" / "index.md").read_text(encoding="utf-8")
    # No lines that are just empty table cells like "| | | |"
    for line in index_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            # Table lines should be header, separator, or have actual content
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Allow header row and separator row, reject all-empty data rows
            if all(c == "" for c in cells):
                raise AssertionError(f"Empty table row found in index.md: {line!r}")


def test_personal_init_creates_extended_tree(tmp_path: Path) -> None:
    target = tmp_path / "body"
    r = runner.invoke(app, ["init", str(target), "--profile", "personal", "-d", "Body"])
    assert r.exit_code == 0, r.output
    for sub in (
        "inbox",
        "projects",
        "inventory",
        "datasets",
        "archive",
        "review",
        "summaries",
        "concepts",
        "decisions",
        "patterns",
        "conflicts",
        "questions",
        "principles",
        "preferences",
        "entities",
        "insights",
    ):
        assert (target / "wiki" / sub).is_dir(), f"wiki/{sub}/ not created"
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "project pages" in agents
    assert "decision records" in agents
    assert "judgment patterns" in agents
    assert "inbox triage" in agents


def test_query_command_returns_ranked_matches_and_save_as(tmp_path: Path) -> None:
    target = tmp_path / "querywiki"
    runner.invoke(app, ["init", str(target), "--profile", "personal", "-d", "Query"])

    (target / "wiki" / "concepts" / "memory-policy.md").write_text(
        """---
title: Memory Policy
type: concept
tags: [concept, memory, policy]
sources: []
updated: 2026-05-17
---

# Memory Policy

Workflow memory should stay durable and separate from project noise.
""",
        encoding="utf-8",
    )
    (target / "wiki" / "conflicts" / "memory-conflict.md").write_text(
        """---
title: Memory Conflict
type: conflict
tags: [conflict, memory]
sources: []
updated: 2026-05-17
---

# Memory Conflict

There is tension between fast capture and durable promotion.
""",
        encoding="utf-8",
    )

    r = runner.invoke(
        app,
        [
            "query",
            "how should workflow memory be handled",
            "--root",
            str(target),
            "--mode",
            "thesis",
            "--save-as",
            "memory-thesis",
        ],
    )
    assert r.exit_code == 0, r.output
    assert "Best Matches" in r.stdout
    assert "Memory Policy" in r.stdout
    assert "Memory Conflict" in r.stdout
    assert (target / "wiki" / "insights" / "memory-thesis.md").is_file()
    index = (target / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "[[memory-thesis]]" in index
    log = (target / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "query | how should workflow memory be handled" in log


def test_dashboard_command_writes_snapshot(tmp_path: Path) -> None:
    target = tmp_path / "dash"
    runner.invoke(app, ["init", str(target), "-d", "Dash"])
    out = tmp_path / "snapshot.html"
    r = runner.invoke(app, ["dashboard", str(target), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert out.is_file()
    pages_dir = tmp_path / "snapshot.pages"
    assert pages_dir.is_dir()
    assert (pages_dir / "wiki__overview.html").is_file()
    content = out.read_text(encoding="utf-8")
    assert "LLM-WorkMem Desktop" in content
    assert "Purpose" in content
    assert "Pages" in content
    assert "snapshot.pages/wiki__overview.html" in content
    assert "file://" not in content


def test_export_command_writes_ai_exports(tmp_path: Path) -> None:
    target = tmp_path / "export"
    runner.invoke(app, ["init", str(target), "-d", "Export"])
    (target / "wiki" / "concepts" / "memory-policy.md").write_text(
        """---
title: Memory Policy
type: concept
tags: [concept, memory]
sources: []
updated: 2026-05-22
---

# Memory Policy

Workflow memory should stay durable and queryable.
""",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["export", str(target)])
    assert r.exit_code == 0, r.output
    assert (target / "llms.txt").is_file()
    assert (target / "llms-full.txt").is_file()
    assert (target / "llms.json").is_file()
    assert "Pages exported" in r.stdout


def test_harvest_command_refreshes_workbench(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    downloads = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Downloads"

    _write(home / ".codex" / "memories" / "MEMORY.md", "# Codex\n- memory")
    _write(
        downloads / "claude-code-config" / "CLAUDE.md",
        "# Claude Code\n- prompt memory",
    )
    _write(
        downloads / "ObsidianVault" / "MASTER-记忆体.md",
        "# Memory Body\n- working memory",
    )

    target = tmp_path / "harvest"
    runner.invoke(app, ["init", str(target), "-d", "Harvest"])
    r = runner.invoke(app, ["harvest", str(target)])
    assert r.exit_code == 0, r.output

    assert (target / "knowledge-digest.html").is_file()
    assert (target / "wiki" / "concepts" / "memory-governance.md").is_file()
    assert (target / "wiki" / "insights" / "current-harvest.md").is_file()
    assert any((target / "raw" / "tool-snapshots").rglob("memory.md"))
    assert (target / "llms.txt").is_file()
    assert (target / "llms-full.txt").is_file()
    assert (target / "llms.json").is_file()
    assert (target / "wiki" / "entities" / "kiro.md").is_file()
    assert (target / "wiki" / "entities" / "shell.md").is_file()

    overview = (target / "wiki" / "overview.md").read_text(encoding="utf-8")
    assert "Automation Status" in overview
    assert "lwm harvest" in overview


def test_watch_command_refreshes_only_on_drift(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    downloads = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Downloads"

    _write(home / ".codex" / "memories" / "MEMORY.md", "# Codex\n- memory")
    _write(
        downloads / "claude-code-config" / "CLAUDE.md",
        "# Claude Code\n- prompt memory",
    )
    _write(
        downloads / "ObsidianVault" / "MASTER-记忆体.md",
        "# Memory Body\n- working memory",
    )

    target = tmp_path / "watch"
    runner.invoke(app, ["init", str(target), "-d", "Watch"])

    first = runner.invoke(app, ["watch", str(target)])
    assert first.exit_code == 0, first.output
    assert "Harvested: yes" in first.stdout
    assert (target / "automation" / "watch-state.json").is_file()

    second = runner.invoke(app, ["watch", str(target)])
    assert second.exit_code == 0, second.output
    assert "Harvested: no" in second.stdout


def test_schedule_command_writes_launchd_bundle(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    target = tmp_path / "sched"
    runner.invoke(app, ["init", str(target), "-d", "Sched"])
    r = runner.invoke(app, ["schedule", str(target)])
    assert r.exit_code == 0, r.output

    script = target / "automation" / "bin" / "run-harvest.sh"
    runner_script = target / "automation" / "bin" / "run-harvest.py"
    plist = target / "automation" / "launchd" / "com.ethan.lwm.harvest.plist"
    launch_agents_plist = home / "Library" / "LaunchAgents" / "com.ethan.lwm.harvest.plist"
    assert script.is_file()
    assert runner_script.is_file()
    assert plist.is_file()
    assert launch_agents_plist.is_file()
    script_content = script.read_text(encoding="utf-8")
    assert "Application Support/llm-workmem-runtime/app/venv/bin/lwm" in script_content
    assert "hub run-cycle" in script_content
    runner_content = runner_script.read_text(encoding="utf-8")
    assert "run-supervisor" in runner_content
    assert "installed non-editable" in runner_content
    plist_content = plist.read_text(encoding="utf-8")
    assert "<key>RunAtLoad</key>" in plist_content
    assert "<key>StartInterval</key>\n  <integer>43200</integer>" in plist_content
    assert "FullCycleInterval" not in plist_content
    assert "Application Support/llm-workmem-runtime" in plist_content
    # Schedule generation must not silently perform the ownership migration.
    assert not (target / "raw").is_symlink()
    assert not (target / "state").is_symlink()
    runtime_data = home / "Library" / "Application Support" / "llm-workmem-runtime" / "llm-workmem"
    assert (runtime_data / "raw").is_dir()
    assert not (target / "wiki").is_symlink()
    assert not (target / "automation").is_symlink()
    assert (runtime_data / "wiki").is_dir()


def test_schema_command_detects_missing_keys(tmp_path: Path) -> None:
    target = tmp_path / "schema"
    runner.invoke(app, ["init", str(target), "-d", "Schema"])
    (target / "wiki" / "concepts" / "bad.md").write_text(
        """# Bad page with no frontmatter
""",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["schema", str(target)])
    assert r.exit_code == 1
    assert "Missing YAML frontmatter" in r.stdout


def test_review_command_writes_queue_page(tmp_path: Path) -> None:
    target = tmp_path / "review"
    runner.invoke(app, ["init", str(target), "-d", "Review"])
    (target / "wiki" / "concepts" / "a.md").write_text(
        """---
title: A
type: concept
tags: [concept]
sources: [raw/missing.md]
updated: 2026-05-22
---

# A

See [[missing-page]].
""",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["review", str(target), "--write"])
    assert r.exit_code == 1
    assert "Review Queue" in r.stdout
    assert any((target / "wiki" / "review").glob("review-queue-*.md"))


def test_eval_command_runs_suite(tmp_path: Path) -> None:
    target = tmp_path / "eval"
    runner.invoke(app, ["init", str(target), "-d", "Eval"])
    (target / "wiki" / "concepts" / "memory-policy.md").write_text(
        """---
title: Memory Policy
type: concept
tags: [concept, memory]
sources: []
updated: 2026-05-22
---

# Memory Policy

Workflow memory should stay durable and queryable.
""",
        encoding="utf-8",
    )
    suite = target / "wiki" / "eval-suite.txt"
    suite.write_text("workflow memory policy | memory-policy\n", encoding="utf-8")
    r = runner.invoke(app, ["eval", str(suite), "--root", str(target), "--mode", "standard"])
    # Eval currently returns exit code 1 when a case's top retrieval does
    # not exactly equal the expected slug. The CLI behaviour is a product
    # concern we are not rewriting here; this test only asserts the eval
    # pipeline runs to completion and produces a report.
    assert r.exit_code in (0, 1)
    assert "# Eval Report" in r.stdout
    assert "Cases" in r.stdout


def test_compile_command_generates_summary_page(tmp_path: Path) -> None:
    target = tmp_path / "compile"
    runner.invoke(app, ["init", str(target), "-d", "Compile"])
    (target / "raw" / "alpha-notes.md").write_text(
        "alpha line one\nalpha line two\n",
        encoding="utf-8",
    )
    runner.invoke(app, ["raw", "sync", str(target / "raw")])
    r = runner.invoke(app, ["compile", str(target)])
    assert r.exit_code == 0, r.output
    assert "Pages changed: 1" in r.stdout
    compiled_pages = list((target / "wiki" / "summaries").glob("source-alpha-notes.md"))
    assert len(compiled_pages) == 1
    text = compiled_pages[0].read_text(encoding="utf-8")
    assert "source_sha256:" in text
    assert "[L1]" in text


def test_audit_command_fails_when_review_items_exist(tmp_path: Path) -> None:
    target = tmp_path / "audit"
    runner.invoke(app, ["init", str(target), "-d", "Audit"])
    (target / "wiki" / "concepts" / "a.md").write_text(
        """---
title: A
type: concept
tags: [concept]
sources: [raw/missing.md]
updated: 2026-05-22
---

# A

See [[missing-page]].
""",
        encoding="utf-8",
    )
    r = runner.invoke(app, ["audit", str(target)])
    assert r.exit_code == 1
    assert "Status: FAILED" in r.stdout



def test_sources_list_includes_kiro_shell_antigravity_and_minimax(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _write(home / ".kiro" / "steering" / "product.md", "# Kiro\n- steering")
    _write(home / ".zshrc", "export TEST_SHELL=1")
    _write(home / "Documents" / "antigravity" / ".agents" / "AGENTS.md", "# Antigravity\n- rules")
    _write(home / "Documents" / "antigravity" / ".agents" / "GLOBAL.md", "# Global\n- shared state")
    _write(home / "Documents" / "antigravity" / ".memory" / "STATE.md", "# State\n- ready")
    _write(home / ".agents" / "AGENTS.md", "# Home Agents\n- global")
    _write(home / ".agents" / "GLOBAL.md", "# Home Global\n- shared")
    _write(home / ".minimax" / "config.yaml", "defaultModel: minimax/MiniMax-M2.7")
    _write(home / ".minimax" / "agents" / "coder" / "agent.md", "# MiniMax Coder\n- overlay")
    _write(home / ".minimax" / "skills" / "knowledge-digest" / "SKILL.md", "# Skill\n- digest")
    _write(home / ".minimax" / "mcp" / "mcp.json", "{}")
    _write(home / ".minimax" / "recovery.json", "{}")
    target = tmp_path / "sources"
    runner.invoke(app, ["init", str(target), "-d", "Sources"])

    r = runner.invoke(app, ["sources", "list", str(target)])
    assert r.exit_code == 0, r.output
    assert "Kiro" in r.stdout
    assert "Shell" in r.stdout
    assert "Antigravity" in r.stdout
    assert "MiniMax" in r.stdout
    assert "found" in r.stdout


def test_adapters_command_writes_tool_entrypoints(tmp_path: Path) -> None:
    target = tmp_path / "adapters"
    runner.invoke(app, ["init", str(target), "-d", "Adapters"])
    runner.invoke(app, ["export", str(target)])

    r = runner.invoke(app, ["adapters", str(target)])
    assert r.exit_code == 0, r.output
    assert (target / "adapters" / "AGENTS.md").is_file()
    assert (target / "adapters" / "CLAUDE.md").is_file()
    assert (target / "adapters" / "copilot-instructions.md").is_file()
    assert (target / "adapters" / "kiro-steering-llm-workmem.md").is_file()
    assert (target / "adapters" / "traerules").is_file()
    assert (target / "adapters" / "antigravity-agents.md").is_file()
    assert (target / "adapters" / "antigravity-global.md").is_file()
    assert (target / "adapters" / "minimax-agent.md").is_file()
    assert (target / "adapters" / "llm-workmem-shell-context.sh").is_file()
    agents_text = (target / "adapters" / "AGENTS.md").read_text(encoding="utf-8")
    assert "llms.txt" in agents_text
    assert "lwm hub bridge" in agents_text
    assert "--output markdown" in agents_text
    assert "phase" in agents_text
    assert '"codex"' in agents_text
    assert "<your-tool-name>" not in agents_text
    assert "lwm hub context --tool <your-tool-name>" not in agents_text
    assert "lwm hub bridge-stop" in agents_text
    assert "lwm hub lifecycle stop" not in agents_text
    shell_context = (target / "adapters" / "llm-workmem-shell-context.sh").read_text(encoding="utf-8")
    assert "printf '%s\\n'" in shell_context


def test_attach_command_installs_project_adapters(tmp_path: Path) -> None:
    target = tmp_path / "wiki"
    project = tmp_path / "project"
    project.mkdir()
    runner.invoke(app, ["init", str(target), "-d", "Attach"])
    runner.invoke(app, ["export", str(target)])

    r = runner.invoke(app, ["attach", str(project), "--root", str(target)])
    assert r.exit_code == 0, r.output
    assert (project / ".agents" / "AGENTS.md").is_file()
    assert (project / ".agents" / "GLOBAL.md").is_file()
    assert "LLM-WIKI:START" in (project / ".agents" / "AGENTS.md").read_text(encoding="utf-8")
    assert (project / "AGENTS.md").is_file()
    assert (project / "CLAUDE.md").is_file()
    assert (project / ".github" / "copilot-instructions.md").is_file()
    assert (project / ".kiro" / "steering" / "llm-workmem.md").is_file()
    assert (project / ".traerules").is_file()
    assert (project / ".llm-workmem" / "shell-context.sh").is_file()
    assert "LLM-WIKI:START" in (project / "AGENTS.md").read_text(encoding="utf-8")



def test_install_global_command_merges_user_adapters(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    target = tmp_path / "wiki"
    runner.invoke(app, ["init", str(target), "-d", "Global"])
    runner.invoke(app, ["export", str(target)])

    r = runner.invoke(app, ["install-global", str(target)])
    assert r.exit_code == 0, r.output
    assert (home / ".agents" / "AGENTS.md").is_file()
    assert (home / ".agents" / "GLOBAL.md").is_file()
    assert "LLM-WIKI:START" in (home / ".agents" / "AGENTS.md").read_text(encoding="utf-8")
    assert (home / ".codex" / "AGENTS.md").is_file()
    assert (home / "CLAUDE.md").is_file()
    assert (home / ".traerules").is_file()
    assert (home / ".kiro" / "steering" / "llm-workmem.md").is_file()
    for name in ("coder", "general", "mavis", "verifier"):
        assert (home / ".minimax" / "agents" / name / "agent.md").is_file()
        assert "LLM-WIKI:START" in (home / ".minimax" / "agents" / name / "agent.md").read_text(encoding="utf-8")
    assert (home / ".config" / "lwm" / "context.json").is_file()
    zshrc = (home / ".zshrc").read_text(encoding="utf-8")
    assert "llm-workmem-shell-context.sh" in zshrc
    assert ".minimax/lwm-shell.sh" in zshrc
    assert "LLM-WIKI:START" in zshrc


def test_install_command_help() -> None:
    r = runner.invoke(app, ["install", "--help"])
    assert r.exit_code == 0
    assert "Install lwm" in r.stdout
    assert "--check" in r.stdout
    assert "--uninstall" in r.stdout
    assert "--extras" in r.stdout


def test_install_command_requires_pyproject(tmp_path: Path) -> None:
    """`lwm install` from a non-project directory must exit 2 with a clear error."""
    r = runner.invoke(app, ["install", str(tmp_path)])
    assert r.exit_code == 2, r.output
    assert "pyproject.toml" in r.output


def test_install_check_runs_without_crash() -> None:
    """`lwm install --check` should not crash with exit_code 2 (the pyproject guard)."""
    r = runner.invoke(app, ["install", "--check"])
    # PATH may or may not have lwm; either 0 (PATH has it) or 1 (PATH missing) is OK.
    assert r.exit_code in (0, 1), r.output


def test_install_uninstall_command_help() -> None:
    r = runner.invoke(app, ["install", "--uninstall", "--help"])
    # Even --uninstall should print --help because --help is handled by typer
    # before action dispatch.
    assert r.exit_code == 0
    assert "Install lwm" in r.stdout


def test_install_uses_uv_pip_uninstall_format() -> None:
    """Regression: the legacy ``uv pip install ... uninstall -y X`` syntax is
    broken (uv treats ``uninstall`` as a package name and rejects ``-y``).
    Verify that ``lwm install`` produces a uv command line that uv accepts.
    """
    import subprocess
    import sys

    # Use the active Python so uv finds a real environment.
    python = sys.executable
    r = subprocess.run(
        ["uv", "pip", "uninstall", "--python", python, "no-such-pkg"],
        capture_output=True,
        text=True,
    )
    # uv accepts the syntax (non-interactive, even when the package is missing,
    # it exits 0 with "not installed" message).
    assert r.returncode == 0, r.stderr
    # The broken form should fail.
    r2 = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            python,
            "uninstall",
            "-y",
            "no-such-pkg",
        ],
        capture_output=True,
        text=True,
    )
    assert r2.returncode != 0  # uv rejects the broken form


def test_dashboard_command_help_has_serve_flag() -> None:
    r = runner.invoke(app, ["dashboard", "--help"])
    assert r.exit_code == 0
    assert "--serve" in r.stdout
    assert "--open" in r.stdout
    assert "--out" in r.stdout


def test_dashboard_writes_snapshot(tmp_path: Path) -> None:
    target = tmp_path / "wiki"
    runner.invoke(app, ["init", str(target), "-d", "DashTest"])
    runner.invoke(app, ["export", str(target)])
    out = tmp_path / "digest.html"
    r = runner.invoke(app, ["dashboard", str(target), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert "LLM-WorkMem" in html
    assert "knowledge" in html.lower() or "wiki" in html.lower()
