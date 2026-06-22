from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mvp_readiness_is_recruit_ai_current() -> None:
    docs = (ROOT / "docs" / "mvp-readiness.md").read_text(encoding="utf-8")
    normalized = " ".join(docs.split())

    assert "recruiting/search-firm intelligence workflow" in normalized
    assert "recruit-ai usage" in docs
    assert "RECRUIT_AI_STORAGE_BACKEND" in docs
    assert "sample=34" in docs
    assert "standard=48" in docs
    assert "developer=52" in docs
    assert "recruit-ai-mcp-0.1.0.mcpb" in docs
    assert "create_candidate" in docs
    assert "add_recruiting_interaction" in docs
    assert "recommend_candidates_for_position" in docs
    assert "smoke-natural-questions --pack recruiting --as-of 2026-06-22" in docs

    assert "sales/deal-intelligence" not in docs
    assert "deal-intel usage" not in docs
    assert "DEAL_INTEL_STORAGE_BACKEND" not in docs
    assert "sample=24" not in docs
    assert "standard=38" not in docs
    assert "developer=42" not in docs
    assert "deal-intel-mcp-0.2.1.mcpb" not in docs
    assert "mcpb pack . deal-intel" not in docs


def test_release_docs_and_workflows_use_recruit_ai_package_name() -> None:
    release_docs = (ROOT / "docs" / "release-publish-checklist.md").read_text(
        encoding="utf-8"
    )
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    staging_workflow = (
        ROOT / ".github" / "workflows" / "staging-smoke.yml"
    ).read_text(encoding="utf-8")

    combined = "\n".join([release_docs, release_workflow, staging_workflow])
    normalized_release_docs = " ".join(release_docs.split())

    assert "recruit-ai-mcp[embedding]" in combined
    assert "recruit-ai-mcp@${PACKAGE_VERSION}" in release_workflow
    assert 'metadata.version("recruit-ai-mcp")' in staging_workflow
    assert "RECRUIT_AI_STORAGE_BACKEND" in staging_workflow
    assert "create_candidate" in combined
    assert "add_recruiting_interaction" in combined
    assert "recommend_candidates_for_position" in combined
    assert "npm `E404`" in release_docs
    assert "No matching distribution found for recruit-ai-mcp" in release_docs
    assert "public `npx` freshness cannot be claimed" in normalized_release_docs
    assert "v0.1.0-rc.1" in release_docs
    assert "Push-Location mcpb" in release_docs
    assert "mcpb validate manifest.json" in release_docs
    assert "mcpb info recruit-ai-mcp-0.1.0.mcpb" in release_docs
    assert "Pop-Location" in release_docs
    assert "MCPB manifest validates and the release artifact is inspectable" in (
        release_docs
    )

    assert "deal-intel-mcp[embedding]" not in combined
    assert "deal-intel-mcp@${PACKAGE_VERSION}" not in combined
    assert 'metadata.version("deal-intel-mcp")' not in combined
    assert "DEAL_INTEL_STORAGE_BACKEND" not in combined
    assert "v0.2.4-rc.1" not in release_docs


def test_bootstrapper_fresh_smoke_uses_recruit_ai_public_package() -> None:
    docs = (ROOT / "docs" / "bootstrapper-fresh-smoke.md").read_text(
        encoding="utf-8"
    )

    assert "recruit-ai-mcp@0.1.0 setup" in docs
    assert "recruit-ai-mcp[embedding]==0.1.0" in docs
    assert "RECRUIT_AI_HOME" in docs
    assert "recruit-ai-mcp-0.1.0.mcpb" in docs
    assert "public registry smoke is still pending publication" in docs
    assert "npm `E404`" in docs
    assert "No matching distribution found for recruit-ai-mcp" in docs
    assert "Do not mark the public `npx recruit-ai-mcp@0.1.0` path ready" in docs

    assert "deal-intel-mcp@0.2.1" not in docs
    assert "deal-intel-mcp[embedding]" not in docs
    assert "DEAL_INTEL_HOME" not in docs


def test_distribution_plan_lists_current_bootstrapper_handoff_commands() -> None:
    docs = (ROOT / "docs" / "distribution-plan.md").read_text(encoding="utf-8")

    assert "npx recruit-ai-mcp setup" in docs
    assert "npx recruit-ai-mcp doctor" in docs
    assert "npx recruit-ai-mcp smoke --profile-only" in docs
    assert "npx recruit-ai-mcp mcpb" in docs
    assert "npx recruit-ai-mcp mcp-config" in docs
    assert "npx recruit-ai-mcp mcp" in docs
    assert "public registry smoke is\npending" in docs

    assert "npx recruit-ai-mcp smoke\nnpx recruit-ai-mcp mcp" not in docs


def test_backlog_current_stream_is_recruit_ai_first() -> None:
    docs = (ROOT / "docs" / "backlog.md").read_text(encoding="utf-8")
    current = docs.split("## Historical Planning Archive", 1)[0]

    assert "### Recruit AI bootstrap roadmap" in current
    assert "recruiter/search-firm intelligence layer" in current
    assert "recruit_ai" in current
    assert "RECRUIT_AI_*" in current
    assert "create_candidate" in current
    assert "recommend_candidates_for_position" in current
    assert "recruiting-first natural-question smoke pack" in current
    assert "smoke-natural-questions --pack recruiting" in current
    assert "### Inherited Deal-Intel Post-v1 / v2 Roadmap" not in current

    assert "deal-intel-mcp==0.2.1" not in current
    assert "deal-intel-mcp@0.2.1" not in current
    assert "mcpb pack . deal-intel-mcp" not in current


def test_agent_entry_docs_are_recruit_ai_first() -> None:
    for relative in ("AGENTS.md", "CLAUDE.md"):
        docs = (ROOT / relative).read_text(encoding="utf-8")

        assert "`recruit-ai-mcp` is a bootstrap fork" in docs
        assert "recruit_ai" in docs
        assert "RECRUIT_AI_STORAGE_BACKEND" in docs
        assert "create_candidate" in docs
        assert "add_recruiting_interaction" in docs
        assert "recommend_candidates_for_position" in docs
        assert "get_recruiting_metrics" in docs
        assert "Avoid hardcoding current tool counts" in docs

        assert "`deal-intel-mcp` is an MCP server for B2B deal intelligence" not in docs
        assert "Current tool count: 42" not in docs
        assert "DEAL_INTEL_STORAGE_BACKEND='local_sample'" not in docs


def test_ai_start_here_matches_current_tool_counts() -> None:
    docs = (ROOT / "AI_START_HERE.md").read_text(encoding="utf-8")

    assert "`sample`: 34 tools" in docs
    assert "`standard` / `full`: 48 tools" in docs
    assert "`developer`: 52 tools" in docs
    assert "get_tool_catalog" in docs

    assert "`sample`: 24 tools" not in docs
    assert "`standard` / `full`: 38 tools" not in docs
    assert "`developer`: 42 tools" not in docs


def test_tool_surface_docs_match_current_counts_and_env_prefix() -> None:
    docs = (ROOT / "docs" / "tool-surfaces.md").read_text(encoding="utf-8")
    normalized = " ".join(docs.split())

    assert "`sample`: 34 tools" in docs
    assert "`standard`: 48 tools" in docs
    assert "`developer`: 52 tools" in docs
    assert "RECRUIT_AI_TOOLS_SURFACE" in docs
    assert "DEAL_INTEL_TOOLS_SURFACE` remains a compatibility fallback" in normalized

    assert "`sample`: 24 tools" not in docs
    assert "`standard`: 38 tools" not in docs
    assert "`developer`: 42 tools" not in docs


def test_mongodb_atlas_pro_docs_use_recruit_ai_cli() -> None:
    docs = (ROOT / "docs" / "mongodb-atlas-pro.md").read_text(encoding="utf-8")

    assert "`recruit-ai render-atlas-dashboard`" in docs
    assert "`recruit-ai mongo refresh-chart-ready`" in docs
    assert "`recruit-ai mongo doctor`" in docs
    assert "`recruit-ai mongo apply-vector-index`" in docs
    assert "`src/deal_intel/cli.py`" in docs

    assert "deal-intel render-atlas-dashboard" not in docs
    assert "deal-intel mongo refresh-chart-ready" not in docs
    assert "deal-intel mongo doctor" not in docs
    assert "deal-intel mongo apply-vector-index" not in docs


def test_baseline_distinguishes_historical_smoke_from_current_surface() -> None:
    docs = (ROOT / "docs" / "baseline.md").read_text(encoding="utf-8")
    normalized = " ".join(docs.split())

    assert "Historical Runtime Snapshot" in docs
    assert "traceability only" in docs
    assert "FastMCP runtime registration at historical smoke time: 9 tools" in docs
    assert "The Python server keeps all 52 handler functions available internally" in docs
    assert "sample 34 tools, standard 48 tools, developer 52 tools" in normalized

    assert "- FastMCP runtime registration: 9 tools" not in docs
    assert "sample 24 tools" not in docs


def test_storage_backend_docs_describe_local_recruiting_persistence() -> None:
    docs = (ROOT / "docs" / "storage-backends.md").read_text(encoding="utf-8")
    normalized = " ".join(docs.split())

    assert "`RECRUIT_AI_STORAGE_BACKEND=local_sample`" in docs
    assert "`recruiting.json`" in docs
    assert "`upsert_recruiting_record`" in docs
    assert "`create_candidate`" in docs
    assert "`add_recruiting_interaction`" in docs
    assert "`recommend_candidates_for_position`" in docs
    assert "strips `raw_content` before persistence" in docs
    assert "DEAL_INTEL_STORAGE_BACKEND` remains a compatibility fallback" in normalized


def test_first_run_docs_include_recruiting_natural_question_pack() -> None:
    for relative in ("README.md", "AI_START_HERE.md", "docs/config-profiles.md"):
        docs = (ROOT / relative).read_text(encoding="utf-8")

        assert "smoke-natural-questions" in docs
        assert "--pack recruiting" in docs
