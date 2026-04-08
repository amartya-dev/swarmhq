"""
Integration tests for the SwarmHQ agent using ADK's AgentEvaluator.

GitHub tools are stubbed via SWARMHQ_TEST_MODE=1 — no binary, no PAT, no
live GitHub connection required. Only a valid GOOGLE_API_KEY (or Vertex AI
credentials) is needed for the LLM calls.

Run locally:
    SWARMHQ_TEST_MODE=1 GOOGLE_API_KEY=... uv run pytest tests/
"""
from __future__ import annotations

import os

# Must be set before swarm_hq_agent is imported anywhere so agent.py picks up
# the mock toolset instead of the real github_mcp_toolset.
os.environ.setdefault("SWARMHQ_TEST_MODE", "1")

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

EVAL_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "swarm_hq_agent",
    "evals",
    "eval.test.json",
)
CONFIG_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "swarm_hq_agent",
    "evals",
    "test_config.json",
)


@pytest.mark.asyncio
async def test_swarmhq_agent_evals() -> None:
    """Run the full ADK eval suite against the SwarmHQ agent with mocked tools."""
    await AgentEvaluator.evaluate(
        agent_module="swarm_hq_agent",
        eval_dataset_file_path_or_dir=EVAL_FILE,
        num_runs=1,
    )
