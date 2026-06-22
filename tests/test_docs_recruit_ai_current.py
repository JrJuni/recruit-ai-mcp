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
