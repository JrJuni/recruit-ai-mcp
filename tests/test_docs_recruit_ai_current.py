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
