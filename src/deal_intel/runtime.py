from __future__ import annotations

import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import deal_intel

PACKAGE_NAME = "deal-intel-mcp"


def build_runtime_diagnostics() -> dict[str, Any]:
    """Return secret-safe runtime location details for install drift debugging."""

    module_file = Path(deal_intel.__file__).resolve()
    try:
        package_version = version(PACKAGE_NAME)
    except PackageNotFoundError:
        package_version = "unknown"

    source_tree = _find_source_tree(module_file)
    source_tree_version = (
        _read_source_tree_version(source_tree) if source_tree is not None else None
    )
    warnings: list[str] = []
    if (
        source_tree_version
        and package_version != "unknown"
        and source_tree_version != package_version
    ):
        warnings.append(
            "Installed package metadata differs from the source tree version. "
            "Reinstall the package or rebuild release artifacts before publishing."
        )

    diagnostics = {
        "package_name": PACKAGE_NAME,
        "package_version": package_version,
        "source_tree_version": source_tree_version,
        "version_mismatch": bool(warnings),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version.split()[0],
        "module_file": str(module_file),
        "package_location": str(module_file.parent),
        "source_tree_root": str(source_tree) if source_tree is not None else None,
        "warnings": warnings,
        "hint": (
            "If Claude/Codex is using a different Python path, update the MCP "
            "Python interpreter path and rerun config doctor."
        ),
    }
    return diagnostics


def _find_source_tree(start: Path) -> Path | None:
    for parent in (start.parent, *start.parents):
        pyproject = parent / "pyproject.toml"
        if not pyproject.exists():
            continue
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        project = data.get("project")
        if isinstance(project, dict) and project.get("name") == PACKAGE_NAME:
            return parent
    return None


def _read_source_tree_version(source_tree: Path | None) -> str | None:
    if source_tree is None:
        return None
    try:
        data = tomllib.loads((source_tree / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    raw_version = project.get("version")
    return raw_version if isinstance(raw_version, str) else None
