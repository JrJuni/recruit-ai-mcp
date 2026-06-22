from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAPPER = ROOT / "npm" / "bin" / "deal-intel-mcp.js"
MCPB_MANIFEST = ROOT / "mcpb" / "manifest.json"
PYPROJECT = ROOT / "pyproject.toml"


def _env_with_home(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["RECRUIT_AI_HOME"] = str(home)
    env.pop("DEAL_INTEL_HOME", None)
    env.pop("RECRUIT_AI_PYTHON", None)
    env.pop("DEAL_INTEL_PYTHON", None)
    return env


def test_npm_package_exposes_expected_bin() -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))

    assert package["name"] == "recruit-ai-mcp"
    assert package["private"] is False
    assert package["publishConfig"] == {"access": "public"}
    assert package["bin"] == {
        "recruit-ai-mcp": "bin/deal-intel-mcp.js",
        "deal-intel-mcp": "bin/deal-intel-mcp.js",
    }
    assert package["engines"]["node"] == ">=18"
    assert "mcpb/" in package["files"]
    assert "dependencies" not in package


def test_npm_bundled_mcpb_matches_package_version() -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    expected = ROOT / "npm" / "mcpb" / f"recruit-ai-mcp-{package['version']}.mcpb"

    assert expected.exists()


def test_release_package_metadata_stays_aligned() -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    manifest = json.loads(MCPB_MANIFEST.read_text(encoding="utf-8"))
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    version = package["version"]

    assert package["name"] == "recruit-ai-mcp"
    assert pyproject["project"]["name"] == package["name"]
    assert manifest["name"] == package["name"]
    assert pyproject["project"]["version"] == version
    assert manifest["version"] == version
    assert package["homepage"] == "https://github.com/JrJuni/recruit-ai-mcp#readme"
    assert pyproject["project"]["urls"]["Repository"] == "https://github.com/JrJuni/recruit-ai-mcp"
    assert manifest["repository"]["url"] == "https://github.com/JrJuni/recruit-ai-mcp"
    assert (ROOT / "mcpb" / f"recruit-ai-mcp-{version}.mcpb").exists()
    assert (ROOT / "npm" / "mcpb" / f"recruit-ai-mcp-{version}.mcpb").exists()

    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    staging_workflow = (ROOT / ".github" / "workflows" / "staging-smoke.yml").read_text(
        encoding="utf-8"
    )
    assert 'npm view "recruit-ai-mcp@${PACKAGE_VERSION}" version' in release_workflow
    assert "npm publish --access public" in release_workflow
    assert 'package_spec="recruit-ai-mcp[embedding]==${PACKAGE_VERSION}"' in staging_workflow
    assert 'metadata.version("recruit-ai-mcp")' in staging_workflow


def test_release_latest_artifact_matches_recruit_ai_version() -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    version = package["version"]
    latest_dir = ROOT / "release" / "latest"
    artifact = latest_dir / f"recruit-ai-mcp-{version}.mcpb"

    assert (latest_dir / "VERSION").read_text(encoding="utf-8").strip() == version
    assert artifact.exists()
    assert not list(latest_dir.glob("deal-intel-mcp-*.mcpb"))
    assert sorted(path.name for path in latest_dir.glob("*.mcpb")) == [
        f"recruit-ai-mcp-{version}.mcpb"
    ]
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
    assert (latest_dir / "checksums.txt").read_text(encoding="utf-8").strip() == (
        f"SHA256  recruit-ai-mcp-{version}.mcpb  {checksum}"
    )


def test_python_package_data_covers_runtime_resources() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]
    resource_root = ROOT / "src" / "deal_intel" / "resources"

    patterns_by_root = []
    for package, patterns in package_data.items():
        package_root = ROOT / "src" / Path(*package.split("."))
        patterns_by_root.extend((package_root, pattern) for pattern in patterns)

    resource_files = [
        path
        for path in resource_root.rglob("*")
        if path.is_file() and path.suffix in {".json", ".yaml", ".yml"}
    ]
    missing = [
        path.relative_to(resource_root).as_posix()
        for path in resource_files
        if not any(
            path.is_relative_to(package_root)
            and fnmatch.fnmatch(
                path.relative_to(package_root).as_posix(),
                pattern,
            )
            for package_root, pattern in patterns_by_root
        )
    ]

    assert missing == []
    assert "defaults.yaml" in package_data["deal_intel.resources"]
    assert "mongo/*.json" in package_data["deal_intel.resources"]
    assert "*.json" in package_data["deal_intel.resources.sample_datasets"]


def test_bootstrapper_where_uses_recruit_ai_home(tmp_path: Path) -> None:
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
    runtime_root = tmp_path / ".recruit-ai" / "runtime"

    assert payload["ok"] is True
    assert payload["bootstrapper_version"] == package["version"]
    assert payload["paths"]["runtime_root"] == str(runtime_root)
    assert payload["paths"]["config_path"] == str(tmp_path / ".recruit-ai" / "config.yaml")
    assert payload["paths"]["install_state_path"] == str(runtime_root / "install-state.json")
    assert payload["mcpb"]["filename"] == f"recruit-ai-mcp-{package['version']}.mcpb"
    assert payload["mcpb"]["local_path"] == str(
        runtime_root / "mcpb" / f"recruit-ai-mcp-{package['version']}.mcpb"
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
    python_path = str(tmp_path / ".recruit-ai" / "runtime" / "venv" / script_dir / python_name)
    server_config = payload["claude_desktop_config_snippet"]["mcpServers"]["recruit-ai-mcp"]

    assert payload["ok"] is True
    assert payload["mcpb"]["filename"] == f"recruit-ai-mcp-{package['version']}.mcpb"
    assert payload["mcpb"]["local_path"] == str(
        tmp_path
        / ".recruit-ai"
        / "runtime"
        / "mcpb"
        / f"recruit-ai-mcp-{package['version']}.mcpb"
    )
    assert payload["mcpb_python_interpreter_path"] == python_path
    assert server_config["command"] == python_path
    assert server_config["args"] == ["-m", "deal_intel.mcp_server"]
    assert server_config["env"]["PYTHONUTF8"] == "1"
    assert "Secrets are not included" in " ".join(payload["notes"])
    assert any("recruiting recommendation" in step for step in payload["mcpb"]["claude_steps"])


def test_bootstrapper_mcp_config_respects_server_name_and_python_override(tmp_path: Path) -> None:
    env = _env_with_home(tmp_path)
    env["RECRUIT_AI_PYTHON"] = sys.executable
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
    assert "RECRUIT_AI_PYTHON" in payload["next_action"]


def test_bootstrapper_setup_dry_run_plans_runtime_install(tmp_path: Path) -> None:
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    version = package["version"]
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
    runtime_root = tmp_path / ".recruit-ai" / "runtime"

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["runtime_root"] == str(runtime_root)
    assert payload["install_spec"] == f"recruit-ai-mcp[embedding]=={version}"
    assert payload["extras"] == ["embedding"]
    assert payload["commands"]["create_venv"]["args"][-1] == str(runtime_root / "venv")
    assert payload["commands"]["install_package"]["args"][-1] == (
        f"recruit-ai-mcp[embedding]=={version}"
    )
    assert payload["commands"]["copy_mcpb"]["to"] == str(
        runtime_root / "mcpb" / f"recruit-ai-mcp-{package['version']}.mcpb"
    )
    assert payload["mcpb"]["local_path"] == str(
        runtime_root / "mcpb" / f"recruit-ai-mcp-{package['version']}.mcpb"
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
    package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
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
    assert payload["install_spec"] == f"recruit-ai-mcp=={package['version']}"
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
    assert payload["mcpb"]["filename"] == f"recruit-ai-mcp-{package['version']}.mcpb"
    assert payload["mcpb"]["bundled_exists"] is True
    assert payload["mcpb"]["local_path"] == str(
        tmp_path
        / ".recruit-ai"
        / "runtime"
        / "mcpb"
        / f"recruit-ai-mcp-{package['version']}.mcpb"
    )
    assert "Install the local MCPB file" in payload["mcpb"]["install_summary"]
    assert any(
        "first client, position, and candidate" in step
        for step in payload["mcpb"]["claude_steps"]
    )
    assert any("recruiting recommendation" in step for step in payload["mcpb"]["claude_steps"])


def test_bootstrapper_mcpb_command_reports_missing_bundle(tmp_path: Path) -> None:
    env = _env_with_home(tmp_path)
    env["RECRUIT_AI_BUNDLED_MCPB_PATH"] = str(tmp_path / "missing.mcpb")
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
    assert "Reinstall recruit-ai-mcp" in payload["next_action"]
