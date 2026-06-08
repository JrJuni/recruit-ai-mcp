from __future__ import annotations

import json

import typer

app = typer.Typer(help="deal-intel CLI")


@app.command("login-chatgpt")
def login_chatgpt(
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-authenticate even with a valid cached token",
    ),
) -> None:
    """Authenticate with ChatGPT OAuth (opens browser). Run once before first use."""
    from deal_intel._env import load_config
    from deal_intel.providers import llm as _llm

    cfg = load_config()
    # Force chatgpt_oauth regardless of defaults so this command always works
    cfg.setdefault("llm", {})["provider"] = "chatgpt_oauth"
    provider = _llm.make_llm_provider(cfg)
    assert isinstance(provider, _llm.ChatGPTOAuthProvider)
    result = provider.login(force=force)
    typer.echo(f"ok  model={result['model']}  token_path={result['token_path']}")


@app.command("backfill-customer-themes")
def backfill_customer_themes(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Write extracted themes to MongoDB. Without this flag, run as dry-run.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Reprocess meetings that already have customer_themes.",
    ),
    limit: int = typer.Option(0, "--limit", min=0, help="Maximum deals to scan; 0 means all."),
) -> None:
    """Extract customer themes for existing meeting records."""
    from deal_intel import _context
    from deal_intel.tools import backfill_customer_themes as _t

    result = _t.handle(
        mongo=_context.mongo(),
        llm=_context.llm_provider(),
        limit=limit,
        force=force,
        dry_run=not apply,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
