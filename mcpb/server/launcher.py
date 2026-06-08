"""Fallback launcher for deal-intel-mcp.

In the standard MCPB install path, Claude Desktop invokes the user's configured
Python interpreter with `-m deal_intel.mcp_server` from the user-specified repo
directory (see mcp_config in manifest.json). This launcher file exists to satisfy
the manifest's `entry_point` field and to provide a direct-invocation fallback
that does the same thing.
"""
from __future__ import annotations

import sys


def main() -> None:
    try:
        from deal_intel.mcp_server import main as _main
    except ImportError as exc:
        sys.stderr.write(
            "deal-intel-mcp launcher: cannot import deal_intel.mcp_server.\n"
            f"  ImportError: {exc}\n"
            "  Set the MCPB user_config 'python_path' to a Python interpreter that has run\n"
            "  `pip install -e .` against this repo (the editable install makes deal_intel\n"
            "  importable without PYTHONPATH).\n"
        )
        raise SystemExit(1)
    _main()


if __name__ == "__main__":
    main()
