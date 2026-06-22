"""Fallback launcher for recruit-ai-mcp.

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
            "recruit-ai-mcp launcher: cannot import deal_intel.mcp_server.\n"
            f"  ImportError: {exc}\n"
            "  Run `npx recruit-ai-mcp setup`, then set the MCPB user_config\n"
            "  'python_path' to the Python interpreter path printed by setup.\n"
        )
        raise SystemExit(1)
    _main()


if __name__ == "__main__":
    main()
