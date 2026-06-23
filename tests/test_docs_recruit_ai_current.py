from pathlib import Path

from scripts.validate_recruiting_smoke import EXPECTED_CONTRACT

ROOT = Path(__file__).resolve().parents[1]


def test_mvp_readiness_is_recruit_ai_current() -> None:
    docs = (ROOT / "docs" / "mvp-readiness.md").read_text(encoding="utf-8")
    normalized = " ".join(docs.split())

    assert "recruiting/search-firm intelligence workflow" in normalized
    assert "recruit-ai usage" in docs
    assert "RECRUIT_AI_STORAGE_BACKEND" in docs
    assert "sample=35" in docs
    assert "standard=49" in docs
    assert "developer=53" in docs
    assert "recruit-ai-mcp-0.1.0.mcpb" in docs
    assert "create_candidate" in docs
    assert "add_recruiting_interaction" in docs
    assert "recommend_candidates_for_position" in docs
    assert "smoke-natural-questions --pack recruiting --as-of 2026-06-22" in docs
    assert "`questions=15`" in docs
    assert (
        "must-have skill evidence gaps, and client shortlist readiness for open sample"
        in normalized
    )
    assert "Public registry `npx recruit-ai-mcp@0.1.0` readiness remains pending" in docs
    assert "disposable `RECRUIT_AI_HOME`" in docs
    assert "macOS fresh-machine smoke remains external-machine evidence" in docs
    assert "current local\n  pre-publish bootstrapper gate" in docs
    assert "after public registry smoke evidence\n  exists" in docs
    assert "Remaining post-bootstrap quality candidates" in docs
    assert "Post-bootstrap tool design cleanup" in docs
    assert "Post-bootstrap tool design candidates" in docs

    assert "sales/deal-intelligence" not in docs
    assert "Remaining post-v2 quality candidates" not in docs
    assert "Post-v2 tool design cleanup" not in docs
    assert "Post-v2 tool design candidates" not in docs
    assert "deal-intel usage" not in docs
    assert "DEAL_INTEL_STORAGE_BACKEND" not in docs
    assert "sample=24" not in docs
    assert "standard=38" not in docs
    assert "developer=42" not in docs
    assert "deal-intel-mcp-0.2.1.mcpb" not in docs
    assert "mcpb pack . deal-intel" not in docs
    assert "current public npx path" not in docs
    assert "`questions=11`" not in docs


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
    assert "actions/checkout@v4" in staging_workflow
    assert "actions/upload-artifact@v4" in release_workflow
    assert (
        "release-smoke-evidence-${{ needs.validate-release.outputs.version }}"
        in release_workflow
    )
    assert "path: smoke-evidence/" in release_workflow
    assert (
        "python -m deal_intel.cli smoke-natural-questions --pack recruiting "
        "--as-of 2026-06-22 --json"
    ) in release_workflow
    assert "smoke-evidence/recruiting-natural-questions.json" in staging_workflow
    assert "current 15-question recruiting pack" in release_docs
    assert f"`candidate_count={EXPECTED_CONTRACT['candidate_count']}`" in release_docs
    assert (
        f"`written_record_count={EXPECTED_CONTRACT['written_record_count']}`"
        in release_docs
    )
    assert (
        f"`guardrail_candidate_count={EXPECTED_CONTRACT['guardrail_candidate_count']}`"
        in release_docs
    )
    assert (
        "`candidate_position_available_count="
        f"{EXPECTED_CONTRACT['candidate_position_available_count']}`"
        in release_docs
    )
    assert (
        "`candidate_position_excluded_count="
        f"{EXPECTED_CONTRACT['candidate_position_excluded_count']}`"
        in release_docs
    )
    assert f"`saved_run_result_count={EXPECTED_CONTRACT['saved_run_result_count']}`" in (
        release_docs
    )
    assert f"`trace_event_count={EXPECTED_CONTRACT['trace_event_count']}`" in (
        release_docs
    )
    assert (
        "`trace_forbidden_value_present="
        f"{EXPECTED_CONTRACT['trace_forbidden_value_present']}`"
        in release_docs
    )
    assert (
        "python scripts/validate_recruiting_smoke.py "
        "smoke-evidence/recruiting-natural-questions.json"
    ) in release_workflow
    assert (
        "python scripts/validate_recruiting_smoke.py "
        "smoke-evidence/recruiting-natural-questions.json"
    ) in staging_workflow
    assert "create_candidate" in combined
    assert "add_recruiting_interaction" in combined
    assert "recommend_candidates_for_position" in combined
    assert "npm `E404`" in release_docs
    assert "No matching distribution found for recruit-ai-mcp" in release_docs
    assert "last checked on 2026-06-23" in release_docs
    assert "public `npx` freshness cannot be claimed" in normalized_release_docs
    assert "v0.1.0-rc.1" in release_docs
    assert "Push-Location mcpb" in release_docs
    assert "mcpb validate manifest.json" in release_docs
    assert "mcpb pack . recruit-ai-mcp-0.1.0.mcpb" in release_docs
    assert "mcpb info recruit-ai-mcp-0.1.0.mcpb" in release_docs
    assert "Pop-Location" in release_docs
    assert "MCPB manifest validates and the release artifact is inspectable" in (
        release_docs
    )

    assert "deal-intel-mcp[embedding]" not in combined
    assert "deal-intel-mcp@${PACKAGE_VERSION}" not in combined
    assert 'metadata.version("deal-intel-mcp")' not in combined
    assert "DEAL_INTEL_STORAGE_BACKEND" not in combined
    assert "smoke-natural-questions --pack deal" not in combined
    assert "v0.2.4-rc.1" not in release_docs
    assert "mcpb validate mcpb\\manifest.json" not in release_docs
    assert "mcpb info mcpb\\recruit-ai-mcp-0.1.0.mcpb" not in release_docs


def test_bootstrapper_fresh_smoke_uses_recruit_ai_public_package() -> None:
    docs = (ROOT / "docs" / "bootstrapper-fresh-smoke.md").read_text(
        encoding="utf-8"
    )
    npm_readme = (ROOT / "npm" / "README.md").read_text(encoding="utf-8")

    assert "recruit-ai-mcp@0.1.0 setup" in docs
    assert "recruit-ai-mcp[embedding]==0.1.0" in docs
    assert "RECRUIT_AI_HOME" in docs
    assert "recruit-ai-mcp-0.1.0.mcpb" in docs
    assert "public registry smoke is still pending publication" in docs
    assert "As of 2026-06-23" in docs
    assert "npm `E404`" in docs
    assert "No matching distribution found for recruit-ai-mcp" in docs
    assert "Do not mark the public `npx recruit-ai-mcp@0.1.0` path ready" in docs
    assert "node npm\\bin\\recruit-ai-mcp.js setup" in docs
    assert "node npm\\bin\\recruit-ai-mcp.js setup" in npm_readme
    assert "## External-Machine Evidence" in docs
    assert "outside the local Windows release gate" in docs
    assert "npx --yes recruit-ai-mcp@0.1.0 setup --python /path/to/python3.11" in docs
    assert "`~/.recruit-ai/runtime/venv/bin/python`" in docs

    assert "deal-intel-mcp@0.2.1" not in docs
    assert "deal-intel-mcp[embedding]" not in docs
    assert "DEAL_INTEL_HOME" not in docs
    assert "node npm\\bin\\deal-intel-mcp.js setup" not in docs
    assert "node npm\\bin\\deal-intel-mcp.js setup" not in npm_readme


def test_distribution_plan_lists_current_bootstrapper_handoff_commands() -> None:
    docs = (ROOT / "docs" / "distribution-plan.md").read_text(encoding="utf-8")

    assert "npx recruit-ai-mcp setup" in docs
    assert "npx recruit-ai-mcp doctor" in docs
    assert "npx recruit-ai-mcp smoke --profile-only" in docs
    assert "npx recruit-ai-mcp mcpb" in docs
    assert "npx recruit-ai-mcp mcp-config" in docs
    assert "npx recruit-ai-mcp mcp" in docs
    assert "public registry smoke is\npending" in docs
    assert "`sample=35`, `standard=49`, `developer=53`" in docs
    assert "Local pre-publish npm/PyPI bootstrapper smoke passed" in docs
    assert "Public registry `npx recruit-ai-mcp@0.1.0` smoke remains pending" in docs
    assert "macOS fresh-machine smoke remains pending as external-machine evidence" in docs
    assert "not\n  as a blocker for the local Windows pre-publish gate" in docs
    assert (
        "uvx recruit-ai-mcp smoke-natural-questions --pack recruiting "
        "--as-of 2026-06-22"
    ) in docs
    assert (
        "recruit-ai smoke-natural-questions --pack recruiting --as-of 2026-06-22"
    ) in docs

    assert "npx recruit-ai-mcp smoke\nnpx recruit-ai-mcp mcp" not in docs
    assert "`sample=24`, `standard=38`, `developer=42`" not in docs
    assert "Public npm/PyPI `npx` smoke passed" not in docs
    assert "recruit-ai-mcp smoke-natural-questions --as-of 2026-06-10" not in docs
    assert "recruit-ai smoke-natural-questions --as-of 2026-06-10" not in docs


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

    assert "`sample`: 35 tools" in docs
    assert "`standard` / `full`: 49 tools" in docs
    assert "`developer`: 53 tools" in docs
    assert "get_tool_catalog" in docs

    assert "`sample`: 24 tools" not in docs
    assert "`standard` / `full`: 38 tools" not in docs
    assert "`developer`: 42 tools" not in docs


def test_first_run_docs_gate_npx_until_publication() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ai_start = (ROOT / "AI_START_HERE.md").read_text(encoding="utf-8")

    assert "After the `recruit-ai-mcp@0.1.0` npm/PyPI packages are published" in readme
    assert "Until the public registry\npublication is complete" in readme
    assert "docs/bootstrapper-fresh-smoke.md" in readme

    assert "once the public `recruit-ai-mcp@0.1.0` npm/PyPI packages are" in ai_start
    assert "use npx for fast usage after publication" in ai_start
    assert "If the user wants the no-git-clone install path after public registry" in ai_start
    assert "Until public registry smoke passes" in ai_start


def test_readme_top_copy_is_recruiting_first() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    top_copy = readme.split("## Architecture At A Glance", maxsplit=1)[0]

    assert "normal recruiting questions" in top_copy
    assert "which candidates\n  best match this role?" in top_copy
    assert "which roles fit this candidate?" in top_copy
    assert "generate a\n  recruiting pipeline report" in top_copy
    assert "not a hosted SaaS that owns your recruiting/team data" in top_copy
    assert "Preserves inherited deal-intelligence compatibility" in top_copy

    assert "which deal needs attention\n  first?" not in top_copy
    assert "what are customers worried about?" not in top_copy
    assert "make this week's pipeline\n  report" not in top_copy
    assert "not a hosted SaaS that owns your deal data" not in top_copy


def test_external_user_test_guide_is_recruit_ai_current() -> None:
    docs = (ROOT / "AI_USER_TEST_GUIDE.md").read_text(encoding="utf-8")

    assert "try Recruit\nAI MCP" in docs
    assert "release/latest/recruit-ai-mcp-0.1.0.mcpb" in docs
    assert "before public registry publication" in docs
    assert "npx recruit-ai-mcp setup" in docs
    assert "recruit-ai-mcp@0.1.0" in docs
    assert "Which candidates best match this open position?" in docs
    assert "Which open positions best fit this candidate?" in docs
    assert "Generate a recruiting pipeline report" in docs
    assert "Recommend candidates for one open position" in docs

    assert "Deal\nIntelligence MCP" not in docs
    assert "deal-intel-mcp" not in docs
    assert "deal-intel-mcp-0.2.1" not in docs
    assert "What is the current pipeline health?" not in docs
    assert "Which deals need attention first?" not in docs
    assert "Generate a weekly pipeline report" not in docs


def test_public_demo_script_is_recruit_ai_first() -> None:
    docs = (ROOT / "docs" / "public-demo-script.md").read_text(encoding="utf-8")

    assert "showing Recruit AI MCP" in docs
    assert "recruiter\nor search-firm team" in docs
    assert "recruiting_pipeline_demo" in docs
    assert "Which candidates best match this open position?" in docs
    assert "Which open positions best fit this candidate?" in docs
    assert "How healthy is the recruiting pipeline?" in docs
    assert "Generate a recruiting pipeline report." in docs
    assert "What client feedback changed the recommendation?" in docs
    assert "recommend_candidates_for_position" in docs
    assert "recommend_positions_for_candidate" in docs
    assert "get_recruiting_metrics" in docs
    assert "export_recruiting_report" in docs
    assert "free/M0 tier is enough" in docs

    assert "showing Deal Intelligence MCP" not in docs
    assert "normal sales questions" not in docs
    assert "How healthy is the current pipeline?" not in docs
    assert "Which deal needs attention first?" not in docs
    assert "Make this week's pipeline report." not in docs


def test_extending_doc_is_recruit_ai_current() -> None:
    docs = (ROOT / "docs" / "extending.md").read_text(encoding="utf-8")

    assert "# Extending recruit-ai-mcp" in docs
    assert "real recruiting/team\ndata" in docs
    assert "still keeps the Python package internals under\n`deal_intel`" in docs
    assert "Change the recruiting fit rubric" in docs
    assert "src/deal_intel/schema/recruiting_fit.py" in docs
    assert "Improve recommendation ranking" in docs
    assert "export_recruiting_report" in docs
    assert "Preserve or customize inherited deal workflows" in docs
    assert "specific recruiting/search motion" in (
        ROOT / "docs" / "README.md"
    ).read_text(encoding="utf-8")

    assert "# Extending deal-intel-mcp" not in docs
    assert "real deal data" not in docs
    assert "customize the server\nfor their own sales motion" not in docs
    assert "specific sales motion" not in (ROOT / "docs" / "README.md").read_text(
        encoding="utf-8"
    )


def test_docs_map_current_streams_are_recruit_ai_current() -> None:
    docs = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    current_streams = docs.split("## Current Product Streams", maxsplit=1)[1]

    assert "Recruit AI profile/config contract" in current_streams
    assert "local personal\n  recruiting persistence path" in current_streams
    assert "Atlas-backed real recruiting/team data" in current_streams
    assert "recommendation-run, metrics, report, local persistence, and\n  smoke" in (
        current_streams
    )

    assert "Z5 profile/config work" not in current_streams
    assert "local\n  personal data as the next target" not in current_streams
    assert "Atlas-backed real team data" not in current_streams


def test_full_install_guide_is_recruit_ai_current() -> None:
    docs = (ROOT / "AI_FULL_INSTALL_GUIDE.md").read_text(encoding="utf-8")

    assert "install `recruit-ai-mcp` in the normal **full** mode" in docs
    assert "real recruiting/team data" in docs
    assert "recruit-ai-mcp@0.1.0" in docs
    assert "recruit-ai-mcp==0.1.0" in docs
    assert "the Python module command still uses inherited `deal_intel` internals" in docs
    assert "~/.recruit-ai" in docs
    assert "cd recruit-ai-mcp" in docs
    assert "Which candidates best match this open position?" in docs
    assert "Which open positions best fit this candidate?" in docs
    assert "Generate a recruiting pipeline report." in docs

    assert "install `deal-intel-mcp`" not in docs
    assert "stores real deal data" not in docs
    assert "~/.deal-intel" not in docs
    assert "cd deal-intel-mcp" not in docs
    assert "Show me the current deal list." not in docs
    assert "Review the riskiest deal." not in docs


def test_tool_surface_docs_match_current_counts_and_env_prefix() -> None:
    docs = (ROOT / "docs" / "tool-surfaces.md").read_text(encoding="utf-8")
    normalized = " ".join(docs.split())

    assert "`sample`: 35 tools" in docs
    assert "`standard`: 49 tools" in docs
    assert "`developer`: 53 tools" in docs
    assert "RECRUIT_AI_TOOLS_SURFACE" in docs
    assert "DEAL_INTEL_TOOLS_SURFACE` remains a compatibility fallback" in normalized

    assert "`sample`: 24 tools" not in docs
    assert "`standard`: 38 tools" not in docs
    assert "`developer`: 42 tools" not in docs


def test_architecture_and_domain_docs_match_current_recruiting_surface() -> None:
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    domain = (ROOT / "docs" / "recruiting-domain-model.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join([architecture, domain])
    normalized_architecture = " ".join(architecture.split())
    normalized_domain = " ".join(domain.split())

    assert "Work 5 exposes these services through MCP" in normalized_architecture
    assert "Work 5 exposes the service paths through MCP" in domain
    assert "Work 5A-B Current Recruiting MCP Tools" in domain
    assert "Tools are visible on `sample`, `standard`, and `developer`." in domain
    assert "Zero-config fixture and local personal use" in architecture
    assert "export_recruiting_report" in combined

    assert "Public MCP registration remains deferred" not in combined
    assert "MCP exposure remain deferred" not in combined
    assert "Public MCP registration, semantic retrieval" not in combined
    assert "Tools are hidden from `sample`" not in normalized_domain


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
    assert "The Python server keeps all 53 handler functions available internally" in docs
    assert "sample 35 tools, standard 49 tools, developer 53 tools" in normalized

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
