"""
Stubbed GitHub toolset used when SWARMHQ_TEST_MODE=1.

Each function mimics the JSON shape returned by the real GitHub MCP server so
the agent's LLM reasoning and delegation logic can be exercised without a live
GitHub connection, a PAT, or the github-mcp-server binary.
"""
from __future__ import annotations

import json
from typing import Any

from google.adk.tools import FunctionTool

# ---------------------------------------------------------------------------
# Canned data
# ---------------------------------------------------------------------------

_MOCK_PROJECTS = {
    "projects": [
        {
            "id": "PVT_mock_001",
            "number": 1,
            "title": "SwarmHQ v1",
            "shortDescription": "Core agent + GitHub integration",
            "public": False,
            "closed": False,
            "url": "https://github.com/orgs/swarmhq-demo/projects/1",
            "items": {
                "totalCount": 4,
                "nodes": [
                    {
                        "id": "PVTI_mock_001",
                        "type": "ISSUE",
                        "fieldValues": {
                            "nodes": [
                                {"name": "In Progress", "field": {"name": "Status"}}
                            ]
                        },
                        "content": {
                            "title": "Deploy agent to Cloud Run",
                            "number": 3,
                            "state": "OPEN",
                        },
                    },
                    {
                        "id": "PVTI_mock_002",
                        "type": "ISSUE",
                        "fieldValues": {
                            "nodes": [
                                {"name": "Todo", "field": {"name": "Status"}}
                            ]
                        },
                        "content": {
                            "title": "Add CI/CD pipeline",
                            "number": 4,
                            "state": "OPEN",
                        },
                    },
                    {
                        "id": "PVTI_mock_003",
                        "type": "ISSUE",
                        "fieldValues": {
                            "nodes": [
                                {"name": "Done", "field": {"name": "Status"}}
                            ]
                        },
                        "content": {
                            "title": "Set up GitHub MCP integration",
                            "number": 1,
                            "state": "CLOSED",
                        },
                    },
                    {
                        "id": "PVTI_mock_004",
                        "type": "ISSUE",
                        "fieldValues": {
                            "nodes": [
                                {"name": "Done", "field": {"name": "Status"}}
                            ]
                        },
                        "content": {
                            "title": "Implement root agent + sub-agents",
                            "number": 2,
                            "state": "CLOSED",
                        },
                    },
                ],
            },
        }
    ]
}

_MOCK_ISSUES = [
    {
        "number": 3,
        "title": "Deploy agent to Cloud Run",
        "state": "open",
        "body": "Set up adk deploy cloud_run with Cloud SQL session persistence.",
        "labels": [{"name": "infra"}],
        "assignees": [],
        "createdAt": "2025-01-10T12:00:00Z",
        "updatedAt": "2025-01-15T08:00:00Z",
        "url": "https://github.com/swarmhq-demo/swarmhq/issues/3",
    },
    {
        "number": 4,
        "title": "Add CI/CD pipeline",
        "state": "open",
        "body": "GitHub Actions workflow: test then deploy to Cloud Run on main.",
        "labels": [{"name": "infra"}, {"name": "ci"}],
        "assignees": [],
        "createdAt": "2025-01-12T09:00:00Z",
        "updatedAt": "2025-01-15T08:00:00Z",
        "url": "https://github.com/swarmhq-demo/swarmhq/issues/4",
    },
]

_MOCK_REPOS = [
    {
        "name": "swarmhq",
        "full_name": "swarmhq-demo/swarmhq",
        "description": "AI-powered project management agent",
        "default_branch": "main",
        "language": "Python",
        "stargazers_count": 0,
        "open_issues_count": 2,
        "url": "https://github.com/swarmhq-demo/swarmhq",
    }
]


# ---------------------------------------------------------------------------
# Stub tool implementations
# ---------------------------------------------------------------------------


def projects_list(**kwargs: Any) -> str:
    return json.dumps(_MOCK_PROJECTS)


def projects_get(**kwargs: Any) -> str:
    projects = _MOCK_PROJECTS["projects"]
    number = kwargs.get("number") or kwargs.get("projectNumber")
    if number:
        match = next((p for p in projects if p["number"] == int(number)), projects[0])
        return json.dumps(match)
    return json.dumps(projects[0] if projects else {})


def issue_read(**kwargs: Any) -> str:
    number = kwargs.get("issue_number") or kwargs.get("number")
    if number:
        match = next(
            (i for i in _MOCK_ISSUES if i["number"] == int(number)), _MOCK_ISSUES[0]
        )
        return json.dumps(match)
    return json.dumps(_MOCK_ISSUES[0])


def list_issues(**kwargs: Any) -> str:
    return json.dumps(_MOCK_ISSUES)


def search_issues(**kwargs: Any) -> str:
    return json.dumps({"total_count": len(_MOCK_ISSUES), "items": _MOCK_ISSUES})


def search_repositories(**kwargs: Any) -> str:
    return json.dumps({"total_count": len(_MOCK_REPOS), "items": _MOCK_REPOS})


def get_file_contents(**kwargs: Any) -> str:
    path = kwargs.get("path", "")
    return json.dumps(
        {
            "type": "file",
            "name": path.split("/")[-1] if path else "README.md",
            "path": path or "README.md",
            "content": "# SwarmHQ\nAI-powered project management agent.\n",
            "encoding": "utf-8",
        }
    )


def get_repository_tree(**kwargs: Any) -> str:
    return json.dumps(
        {
            "tree": [
                {"path": "swarm_hq_agent/agent.py", "type": "blob"},
                {"path": "swarm_hq_agent/guardrails.py", "type": "blob"},
                {"path": "swarm_hq_agent/state_tools.py", "type": "blob"},
            ]
        }
    )


def list_branches(**kwargs: Any) -> str:
    return json.dumps([{"name": "main"}, {"name": "dev"}])


def get_me(**kwargs: Any) -> str:
    return json.dumps({"login": "swarmhq-bot", "id": 99999, "type": "User"})


def get_teams(**kwargs: Any) -> str:
    return json.dumps([{"name": "engineering", "slug": "engineering", "privacy": "closed"}])


def list_pull_requests(**kwargs: Any) -> str:
    return json.dumps([
        {
            "number": 27,
            "title": "Refactor auth module",
            "state": "open",
            "user": {"login": "anmolgaur45"},
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T10:00:00Z",
            "url": "https://github.com/swarmhq-demo/tiny-blog/pull/27",
        }
    ])


# ---------------------------------------------------------------------------
# Exported tool lists (drop-in replacements for real McpToolset lists)
# ---------------------------------------------------------------------------

github_pm_tools: list[FunctionTool] = [
    FunctionTool(func=projects_list),
    FunctionTool(func=projects_get),
    FunctionTool(func=issue_read),
    FunctionTool(func=list_issues),
    FunctionTool(func=search_issues),
    FunctionTool(func=get_me),
    FunctionTool(func=get_teams),
]

github_code_tools: list[FunctionTool] = [
    FunctionTool(func=search_repositories),
    FunctionTool(func=get_file_contents),
    FunctionTool(func=get_repository_tree),
    FunctionTool(func=list_branches),
    FunctionTool(func=get_me),
]

github_risk_tools: list[FunctionTool] = [
    FunctionTool(func=search_repositories),
    FunctionTool(func=list_pull_requests),
    FunctionTool(func=list_issues),
    FunctionTool(func=list_branches),
    FunctionTool(func=get_me),
]
