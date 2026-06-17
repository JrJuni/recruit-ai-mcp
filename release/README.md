# Release Artifacts

This folder contains ready-to-install release artifacts for users who should not
have to rebuild the MCPB package locally.

## Latest

- `latest/deal-intel-mcp-0.2.1.mcpb`

The MCPB installs the Claude Desktop extension manifest and launcher. It does
not bundle the Python package or dependencies. Users still need to install this
repository into a Python environment first, then provide that interpreter path
in the MCPB install form.

Use `latest/VERSION` and `latest/checksums.txt` to confirm the artifact version
and checksum before handing it to a tester.

## Update Policy

- Keep the newest public-ready MCPB in `release/latest/`.
- Update `release/latest/checksums.txt` whenever the MCPB changes.
- GitHub Releases should attach the same MCPB file for easier download.
- Do not put secrets, local config files, or generated reports in this folder.
