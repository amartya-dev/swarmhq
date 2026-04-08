## SwarmHQ

ADK agent team for **executive-friendly**:
- **Project progress/status**
- **Feature planning**
- **Bug/problem scoping**

Hard scope: it will refuse requests outside those categories.

### Architecture
- **Coordinator**: `swarm_hq_agent` (exec-facing)
- **Product Manager specialist**: Projects + Issues (writes allowed)
- **Code Analyzer specialist**: org-wide repo/code analysis (read-only)
- **Project Health Agent specialist**: org-wide project health and delivery risk analysis (read-only)

All GitHub access is **scoped to the org** `swarmhq-demo`.

### Demo scenario

The system's core differentiation is visible when you ask a status question like "How is the auth refactor going?" The PM specialist reads the project board and reports the feature as in progress. The Project Health Agent independently checks GitHub activity and finds the PR has had no commits in over a week. The Coordinator surfaces both views and explicitly calls out the disagreement — giving the executive the signal that the board does not reflect reality, without requiring them to dig into GitHub themselves.

### Setup

#### 1) Python dependencies

This repo is configured for Python `3.14` (see `.python-version`).

Using `uv`:

```bash
uv sync
```

#### 2) GitHub MCP server binary

Download the `github-mcp-server` binary and place it at:
- `./swarm_hq_agent/bin/github-mcp-server`

Make it executable:

```bash
chmod +x ./swarm_hq_agent/bin/github-mcp-server
```

#### 3) Environment variables

Copy the template and fill in values:

```bash
cp swarm_hq_agent/.env.example swarm_hq_agent/.env
```

Required:
- **`GITHUB_PERSONAL_ACCESS_TOKEN`**: PAT with access to org repos/projects and permission to write Issues/Projects if you want write operations.
  - If a token was ever pasted into code/logs or shared unintentionally, **rotate it immediately**.

Model auth (choose one):
- **Gemini API**: set `GOOGLE_API_KEY`
- **Vertex AI**: set `GOOGLE_GENAI_USE_VERTEXAI=1`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`

### Run

From the repo root:

```bash
adk run swarm_hq_agent
```

Or start the dev web UI:

```bash
adk web --port 8000
```

### Configuration

- **Org scope**: `swarm_hq_agent/guardrails.py` (`ORG_OWNER`)
- **GitHub tool permissions**:
  - PM toolset: `swarm_hq_agent/mcps/github_mcp_toolset.py` (`github_pm_tools`)
  - Code toolset: `swarm_hq_agent/mcps/github_mcp_toolset.py` (`github_code_tools`, read-only)

### Demo seed + deployment docs

- **Demo GitHub seed state (simple)**: `docs/demo-github-seed.md`
- **Local testing (ADK API + example prompts)**: `docs/local-testing.md`
- **Cloud Run deployment plan (GitHub MCP over stdio + PAT)**: `docs/cloud-run-deployment.md`

