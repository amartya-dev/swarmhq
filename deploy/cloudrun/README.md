# Cloud Run scaffold (copy/paste)

This folder contains a minimal Cloud Run-friendly wrapper around ADK, plus a Dockerfile that also installs `github-mcp-server` so SwarmHQ can use GitHub via local MCP stdio in production.

## Files

- `main.py`: FastAPI app wrapper around ADK (`get_fast_api_app`), binds to `$PORT`.
- `requirements.txt`: runtime dependencies for the Cloud Run container.
- `Dockerfile`: installs deps and downloads/installs `github-mcp-server`.

## How to use

Copy these into repo root before deployment:

- `deploy/cloudrun/main.py` → `./main.py`
- `deploy/cloudrun/requirements.txt` → `./requirements.txt`
- `deploy/cloudrun/Dockerfile` → `./Dockerfile`

Then follow `docs/cloud-run-deployment.md`.

## Important

- You must replace the `GITHUB_MCP_SERVER_URL` placeholder in the Dockerfile with the correct release URL for your `github-mcp-server` binary (Linux build).
- Start with Cloud Run `--concurrency 1` until validated.
- For hackathon demos, set `ADK_WITH_UI=true` so the web chat UI is served.
