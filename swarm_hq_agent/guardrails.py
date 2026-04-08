from __future__ import annotations

from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import Client
import os

from google.genai import types

ORG_OWNER = os.getenv("SWARMHQ_ORG_OWNER", "swarmhq-demo").strip() or "swarmhq-demo"

_CLASSIFIER_MODEL = "gemini-2.0-flash-lite"
_CLASSIFIER_PROMPT = """\
You are a strict single-label intent classifier for a software project-management assistant.

Reply with ONLY one of these two tokens — no punctuation, no explanation:
  IN_SCOPE    — the query is about software project progress/status, feature planning, or bug/incident scoping
  OUT_OF_SCOPE — anything else

Query: {query}"""

_genai_client: Client | None = None


def _get_genai_client() -> Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = Client()
    return _genai_client


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


async def scope_guardrail_before_model(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Uses a fast LLM classifier to decide whether the user query is within scope:
    - project progress/status
    - feature planning
    - bug/problem scoping

    Returns an LlmResponse to block; returns None to allow.
    """
    text = _last_user_text(llm_request).strip()
    if not text:
        return None

    client = _get_genai_client()
    result = await client.aio.models.generate_content(
        model=_CLASSIFIER_MODEL,
        contents=_CLASSIFIER_PROMPT.format(query=text),
    )
    label = (result.text or "").strip().upper()

    if "IN_SCOPE" in label:
        return None

    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    text=(
                        "I can only help with project progress, planning new features, "
                        "or scoping bugs/problems. If you share which of those you need "
                        "and a short description, I'll take it from there."
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

        if tool_name in {"transfer_to_agent", "read_team_context"}:
            return None

        if tool_name == "projects_list" and "method" not in args:
            args["method"] = "list_projects"
        if tool_name == "projects_get" and "method" not in args:
            args["method"] = "get_project"
        if tool_name == "issue_read" and "method" not in args:
            args["method"] = "get"

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

        for key in ("owner", "org", "item_owner"):
            if key in args and args[key] and args[key] != org_owner:
                return {
                    "status": "error",
                    "error_message": (
                        f"Blocked: this system is scoped to GitHub org '{org_owner}'. "
                        f"Received {key}='{args[key]}'."
                    ),
                }

        if "repo" in args and args.get("owner") and args["owner"] != org_owner:
            return {
                "status": "error",
                "error_message": (
                    f"Blocked: repository operations must use owner '{org_owner}'."
                ),
            }

        if agent_mode == "code":
            if tool_name.startswith(_WRITE_TOOL_NAME_HINTS):
                return {
                    "status": "error",
                    "error_message": (
                        "Blocked: the code analyzer is read-only and cannot perform write operations."
                    ),
                }
            return None

        if agent_mode == "pm":
            if tool_name.startswith(allowed_pm_prefixes):
                return None
            if tool_name.startswith(_WRITE_TOOL_NAME_HINTS):
                return {
                    "status": "error",
                    "error_message": (
                        "Blocked: this agent is limited to Projects and Issues operations."
                    ),
                }
            return None

        if agent_mode == "coordinator":
            return {
                "status": "error",
                "error_message": "Blocked: coordinator cannot call GitHub tools directly.",
            }

        return None

    return _callback
