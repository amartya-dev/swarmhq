from __future__ import annotations

from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
import os

from google.genai import types

# Default org scope for GitHub access. Override via env for demos/tests.
ORG_OWNER = os.getenv("SWARMHQ_ORG_OWNER", "swarmhq-demo").strip() or "swarmhq-demo"


def _last_user_text(llm_request: LlmRequest) -> str:
    if not llm_request.contents:
        return ""
    for content in reversed(llm_request.contents):
        if content.role != "user":
            continue
        if not content.parts:
            continue
        part0 = content.parts[0]
        text = getattr(part0, "text", None)
        if text:
            return text
    return ""


def scope_guardrail_before_model(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Hard-scope this app to only:
    - project progress/status
    - feature planning
    - bug/problem scoping

    Return an LlmResponse to block; return None to allow.
    """
    text = _last_user_text(llm_request).strip()
    if not text:
        return None

    t = text.lower()

    # Very permissive keyword-based allowlist. We prefer false positives (allow)
    # to avoid blocking legitimate queries; tool-callback scoping provides a
    # second layer of enforcement for GitHub access.
    allow_markers = (
        "status",
        "progress",
        "roadmap",
        "milestone",
        "timeline",
        "delivery",
        "ship",
        "release",
        "plan",
        "feature",
        "enhancement",
        "request",
        "bug",
        "issue",
        "incident",
        "problem",
        "error",
        "regression",
        "outage",
        "broken",
        "crash",
        "failing",
        "latency",
        "performance",
    )

    if any(m in t for m in allow_markers):
        return None

    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    text=(
                        "I can only help with project progress, planning new features, "
                        "or scoping bugs/problems. If you share which of those you need "
                        "and a short description, I’ll take it from there."
                    )
                )
            ],
        )
    )


_WRITE_TOOL_NAME_HINTS = (
    "create_",
    "update_",
    "delete_",
    "merge_",
    "push_",
    "star_",
    "unstar_",
    "assign_",
    "request_",
    "dismiss_",
    "manage_",
    "mark_",
    "fork_",
)


def github_scope_guardrail_before_tool(
    *,
    org_owner: str = ORG_OWNER,
    agent_mode: str,
):
    """
    Factory returning a before_tool_callback that:
    - forces GitHub org scoping (owner/org/item_owner) to `org_owner`
    - blocks writes for `agent_mode="code"`
    - blocks out-of-scope write tools for `agent_mode="pm"` (defense-in-depth)
    """

    allowed_pm_prefixes = (
        # Projects / Issues toolsets (read + write)
        "projects_",
        "issue_",
        "sub_issue_",
        "add_issue_comment",
        "get_label",
        "list_label",
        "label_write",
        # Context / discovery
        "get_me",
        "get_teams",
        "get_team_members",
        "search_issues",
        "list_issues",
        # Repo metadata reads
        "get_file_contents",
        "get_repository_tree",
        "list_branches",
        "list_commits",
        "search_code",
        "search_repositories",
    )

    def _callback(
        tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
    ) -> Optional[dict[str, Any]]:
        tool_name = tool.name or ""

        # Always allow local coordination tools.
        if tool_name in {"transfer_to_agent", "read_team_context"}:
            return None

        # Improve robustness of GitHub MCP calls: auto-fill common required fields
        # that LLMs sometimes omit (e.g., "method" for *_list/*_read tools).
        if tool_name == "projects_list" and "method" not in args:
            args["method"] = "list_projects"
        if tool_name == "projects_get" and "method" not in args:
            args["method"] = "get_project"
        if tool_name == "issue_read" and "method" not in args:
            args["method"] = "get"

        # Default org owner where common GitHub tools require it.
        if tool_name in {
            "projects_list",
            "projects_get",
            "projects_write",
            "issue_read",
            "issue_write",
            "list_issues",
            "search_issues",
            "get_label",
            "list_label",
            "label_write",
            "list_branches",
            "list_commits",
            "get_commit",
            "get_file_contents",
            "get_repository_tree",
            "search_code",
        }:
            args.setdefault("owner", org_owner)

        # Enforce org scoping whenever an org/owner-like parameter exists.
        # The GitHub MCP server tools commonly use `owner` and sometimes `org`.
        # We also handle `item_owner` used by some project-item writes.
        for key in ("owner", "org", "item_owner"):
            if key in args and args[key] and args[key] != org_owner:
                return {
                    "status": "error",
                    "error_message": (
                        f"Blocked: this system is scoped to GitHub org '{org_owner}'. "
                        f"Received {key}='{args[key]}'."
                    ),
                }

        # Enforce that if both owner+repo are provided, owner must be org_owner.
        if "repo" in args and args.get("owner") and args["owner"] != org_owner:
            return {
                "status": "error",
                "error_message": (
                    f"Blocked: repository operations must use owner '{org_owner}'."
                ),
            }

        # Code agent: block anything that looks like a write.
        if agent_mode == "code":
            if tool_name.startswith(_WRITE_TOOL_NAME_HINTS):
                return {
                    "status": "error",
                    "error_message": (
                        "Blocked: the code analyzer is read-only and cannot perform write operations."
                    ),
                }
            return None

        # PM agent: allow only projects/issues-centric tools (+ safe reads).
        if agent_mode == "pm":
            if tool_name.startswith(allowed_pm_prefixes):
                return None
            # If a tool looks like a write and isn't in the allowlist, block it.
            if tool_name.startswith(_WRITE_TOOL_NAME_HINTS):
                return {
                    "status": "error",
                    "error_message": (
                        "Blocked: this agent is limited to Projects and Issues operations."
                    ),
                }
            return None

        # Coordinator should not be calling GitHub MCP tools directly.
        if agent_mode == "coordinator":
            return {
                "status": "error",
                "error_message": "Blocked: coordinator cannot call GitHub tools directly.",
            }

        return None

    return _callback
