import os
from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

repo_root = Path(__file__).resolve().parents[2]
default_bin = repo_root / "bin" / "github-mcp-server"

github_mcp_command = os.getenv("GITHUB_MCP_COMMAND", str(default_bin))
if not Path(github_mcp_command).exists():
    raise RuntimeError(
        f"GitHub MCP server binary not found at {github_mcp_command}. "
        "Download it into ./bin/github-mcp-server or set GITHUB_MCP_COMMAND."
    )

# Auth for local server is passed via environment.
# `github-mcp-server` expects GITHUB_PERSONAL_ACCESS_TOKEN.
github_token = (
    os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    or os.getenv("GITHUB_MCP_PAT")
    or os.getenv("GITHUB_PAT")
    or os.getenv("GITHUB_TOKEN")
)
if not github_token:
    raise RuntimeError(
        "Missing GitHub auth token for local github-mcp-server. "
        "Set GITHUB_PERSONAL_ACCESS_TOKEN (preferred) or GITHUB_MCP_PAT / GITHUB_PAT."
    )

server_env: dict[str, str] = {
    "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
    # Also set common aliases to keep other tooling happy.
    "GITHUB_TOKEN": github_token,
    # Force github.com for this project.
    # (A mismatched GITHUB_HOST commonly surfaces as "owner not found".)
    "GITHUB_HOST": "https://github.com",
}


def _mcp_toolset(*, args: list[str]) -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=github_mcp_command,
                args=args,
                env=server_env,
                cwd=str(repo_root),
            )
        ),
    )


_insiders = os.getenv("GITHUB_MCP_INSIDERS", "").lower() in {"1", "true", "yes"}

# Product-manager toolset: Projects + Issues (and minimal supporting context).
# NOTE: We intentionally do NOT include pull_requests/git toolsets here.
github_pm_tools = [
    _mcp_toolset(
        args=[
            "stdio",
            "--toolsets",
            "context,projects,issues,users,repos",
            *(["--insiders"] if _insiders else []),
        ]
    )
]

# Code-analyzer toolset: repo/code reading only.
# Defense-in-depth: run MCP server in read-only mode and limit toolsets.
github_code_tools = [
    _mcp_toolset(
        args=[
            "stdio",
            "--read-only",
            "--toolsets",
            "context,repos,git,users",
            *(["--insiders"] if _insiders else []),
        ]
    )
]

# Project Health Agent toolset: read-only, adds pull_requests for stale PR / review analysis.
github_risk_tools = [
    _mcp_toolset(
        args=[
            "stdio",
            "--read-only",
            "--toolsets",
            "context,repos,git,users,pull_requests,issues",
            *(["--insiders"] if _insiders else []),
        ]
    )
]
