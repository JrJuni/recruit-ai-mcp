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
    assert "recruit-ai-mcp-0.2.3.mcpb" in docs
    assert "create_candidate" in docs
    assert "add_recruiting_interaction" in docs
    assert "recommend_candidates_for_position" in docs

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

    assert "recruit-ai-mcp[embedding]" in combined
    assert "recruit-ai-mcp@${PACKAGE_VERSION}" in release_workflow
    assert 'metadata.version("recruit-ai-mcp")' in staging_workflow
    assert "RECRUIT_AI_STORAGE_BACKEND" in staging_workflow
    assert "create_candidate" in combined
    assert "add_recruiting_interaction" in combined
    assert "recommend_candidates_for_position" in combined

    assert "deal-intel-mcp[embedding]" not in combined
    assert "deal-intel-mcp@${PACKAGE_VERSION}" not in combined
    assert 'metadata.version("deal-intel-mcp")' not in combined
    assert "DEAL_INTEL_STORAGE_BACKEND" not in combined


def test_bootstrapper_fresh_smoke_uses_recruit_ai_public_package() -> None:
    docs = (ROOT / "docs" / "bootstrapper-fresh-smoke.md").read_text(
        encoding="utf-8"
    )

    assert "recruit-ai-mcp@0.2.3 setup" in docs
    assert "recruit-ai-mcp[embedding]==0.2.3" in docs
    assert "RECRUIT_AI_HOME" in docs
    assert "recruit-ai-mcp-0.2.3.mcpb" in docs

    assert "deal-intel-mcp@0.2.1" not in docs
    assert "deal-intel-mcp[embedding]" not in docs
    assert "DEAL_INTEL_HOME" not in docs


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
