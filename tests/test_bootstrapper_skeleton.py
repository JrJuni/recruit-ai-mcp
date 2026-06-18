from __future__ import annotations

import json
import os
import subprocess
import sys
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
    assert package["private"] is False
    assert package["publishConfig"] == {"access": "public"}
    assert package["bin"] == {"deal-intel-mcp": "bin/deal-intel-mcp.js"}
    assert package["engines"]["node"] == ">=18"
    assert "mcpb/" in package["files"]
    assert "dependencies" not in package


def test_npm_bundled_mcpb_matches_package_version() -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    expected = ROOT / "npm" / "mcpb" / f"deal-intel-mcp-{package['version']}.mcpb"

    assert expected.exists()


def test_bootstrapper_where_uses_deal_intel_home(tmp_path: Path) -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
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
    assert payload["bootstrapper_version"] == package["version"]
    assert payload["paths"]["runtime_root"] == str(runtime_root)
    assert payload["paths"]["config_path"] == str(tmp_path / ".deal-intel" / "config.yaml")
    assert payload["paths"]["install_state_path"] == str(runtime_root / "install-state.json")
    assert payload["mcpb"]["filename"] == f"deal-intel-mcp-{package['version']}.mcpb"
    assert payload["mcpb"]["local_path"] == str(
        runtime_root / "mcpb" / f"deal-intel-mcp-{package['version']}.mcpb"
    )
    assert payload["mcpb"]["bundled_exists"] is True


def test_bootstrapper_mcp_config_outputs_claude_snippet(tmp_path: Path) -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    result = subprocess.run(
        ["node", str(BOOTSTRAPPER), "mcp-config", "--json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)
    script_dir = "Scripts" if os.name == "nt" else "bin"
    python_name = "python.exe" if os.name == "nt" else "python"
    python_path = str(tmp_path / ".deal-intel" / "runtime" / "venv" / script_dir / python_name)
    server_config = payload["claude_desktop_config_snippet"]["mcpServers"]["deal-intel-mcp"]

    assert payload["ok"] is True
    assert payload["mcpb"]["filename"] == f"deal-intel-mcp-{package['version']}.mcpb"
    assert payload["mcpb"]["local_path"] == str(
        tmp_path / ".deal-intel" / "runtime" / "mcpb" / f"deal-intel-mcp-{package['version']}.mcpb"
    )
    assert payload["mcpb_python_interpreter_path"] == python_path
    assert server_config["command"] == python_path
    assert server_config["args"] == ["-m", "deal_intel.mcp_server"]
    assert server_config["env"]["PYTHONUTF8"] == "1"
    assert "Secrets are not included" in " ".join(payload["notes"])
    assert any("add_interaction" in step for step in payload["mcpb"]["claude_steps"])


def test_bootstrapper_mcp_config_respects_server_name_and_python_override(tmp_path: Path) -> None:
    env = _env_with_home(tmp_path)
    env["DEAL_INTEL_PYTHON"] = sys.executable
    result = subprocess.run(
        ["node", str(BOOTSTRAPPER), "mcp-config", "--json", "--server-name", "custom-deals"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )

    payload = json.loads(result.stdout)
    server_config = payload["claude_desktop_config_snippet"]["mcpServers"]["custom-deals"]

    assert payload["server_name"] == "custom-deals"
    assert payload["mcpb_python_interpreter_path"] == sys.executable
    assert server_config["command"] == sys.executable


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


def test_bootstrapper_setup_dry_run_plans_runtime_install(tmp_path: Path) -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    result = subprocess.run(
        [
            "node",
            str(BOOTSTRAPPER),
            "setup",
            "--dry-run",
            "--json",
            "--python",
            sys.executable,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)
    runtime_root = tmp_path / ".deal-intel" / "runtime"

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["runtime_root"] == str(runtime_root)
    assert payload["install_spec"] == "deal-intel-mcp[embedding]==0.2.3"
    assert payload["extras"] == ["embedding"]
    assert payload["commands"]["create_venv"]["args"][-1] == str(runtime_root / "venv")
    assert payload["commands"]["install_package"]["args"][-1] == "deal-intel-mcp[embedding]==0.2.3"
    assert payload["commands"]["copy_mcpb"]["to"] == str(
        runtime_root / "mcpb" / f"deal-intel-mcp-{package['version']}.mcpb"
    )
    assert payload["mcpb"]["local_path"] == str(
        runtime_root / "mcpb" / f"deal-intel-mcp-{package['version']}.mcpb"
    )
    assert payload["commands"]["post_install_check"]["args"] == [
        "-m",
        "deal_intel.cli",
        "smoke-profile",
        "--profile",
        "sample",
    ]
    assert not (runtime_root / "install-state.json").exists()


def test_bootstrapper_setup_lightweight_uses_base_package(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "node",
            str(BOOTSTRAPPER),
            "setup",
            "--dry-run",
            "--json",
            "--lightweight",
            "--python",
            sys.executable,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)
    assert payload["install_spec"] == "deal-intel-mcp==0.2.3"
    assert payload["extras"] == []


def test_bootstrapper_setup_rejects_unknown_source(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "node",
            str(BOOTSTRAPPER),
            "setup",
            "--dry-run",
            "--json",
            "--source",
            "branch",
            "--python",
            sys.executable,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["ok"] is False
    assert payload["error"] == "invalid_setup_option"


def test_bootstrapper_mcpb_command_outputs_local_handoff(tmp_path: Path) -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    result = subprocess.run(
        ["node", str(BOOTSTRAPPER), "mcpb", "--json"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_env_with_home(tmp_path),
    )

    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["mcpb"]["filename"] == f"deal-intel-mcp-{package['version']}.mcpb"
    assert payload["mcpb"]["bundled_exists"] is True
    assert payload["mcpb"]["local_path"] == str(
        tmp_path / ".deal-intel" / "runtime" / "mcpb" / f"deal-intel-mcp-{package['version']}.mcpb"
    )
    assert "Install the local MCPB file" in payload["mcpb"]["install_summary"]
    assert any("first meeting note" in step for step in payload["mcpb"]["claude_steps"])
    assert any("add_interaction" in step for step in payload["mcpb"]["claude_steps"])


def test_bootstrapper_mcpb_command_reports_missing_bundle(tmp_path: Path) -> None:
    env = _env_with_home(tmp_path)
    env["DEAL_INTEL_BUNDLED_MCPB_PATH"] = str(tmp_path / "missing.mcpb")
    result = subprocess.run(
        ["node", str(BOOTSTRAPPER), "mcpb", "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )

    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["ok"] is False
    assert payload["error"] == "bundled_mcpb_missing"
    assert "Reinstall deal-intel-mcp" in payload["next_action"]
