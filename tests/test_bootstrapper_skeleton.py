from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAPPER = ROOT / "npm" / "bin" / "deal-intel-mcp.js"


def _env_with_home(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DEAL_INTEL_HOME"] = str(home)
    env.pop("DEAL_INTEL_PYTHON", None)
    return env


def test_npm_package_exposes_expected_bin() -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))

    assert package["name"] == "deal-intel-mcp"
    assert package["private"] is True
    assert package["bin"] == {"deal-intel-mcp": "bin/deal-intel-mcp.js"}
    assert package["engines"]["node"] == ">=18"
    assert "dependencies" not in package


def test_bootstrapper_where_uses_deal_intel_home(tmp_path: Path) -> None:
    result = subprocess.run(
        ["node", str(BOOTSTRAPPER), "where", "--json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)
    runtime_root = tmp_path / ".deal-intel" / "runtime"

    assert payload["ok"] is True
    assert payload["paths"]["runtime_root"] == str(runtime_root)
    assert payload["paths"]["config_path"] == str(tmp_path / ".deal-intel" / "config.yaml")
    assert payload["paths"]["install_state_path"] == str(runtime_root / "install-state.json")


def test_bootstrapper_missing_runtime_is_actionable(tmp_path: Path) -> None:
    result = subprocess.run(
        ["node", str(BOOTSTRAPPER), "doctor", "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["ok"] is False
    assert payload["error"] == "runtime_python_missing"
    assert "DEAL_INTEL_PYTHON" in payload["next_action"]
