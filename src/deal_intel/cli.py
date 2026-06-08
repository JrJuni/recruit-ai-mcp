from __future__ import annotations

import typer

app = typer.Typer(help="deal-intel CLI")


@app.command("login-chatgpt")
def login_chatgpt(
    force: bool = typer.Option(False, "--force", help="Re-authenticate even with a valid cached token"),
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


if __name__ == "__main__":
    app()
