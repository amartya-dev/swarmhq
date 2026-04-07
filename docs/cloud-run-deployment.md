# Cloud Run deployment plan (ADK + GitHub MCP over local stdio)

This plan matches the current architecture where SwarmHQ spawns `github-mcp-server` locally over stdio (see `swarm_hq_agent/mcps/github_mcp_toolset.py`) and passes auth via environment variables.

## Key constraints

- Cloud Run runs **Linux** containers, so your `github-mcp-server` must be a **Linux** build.
- The GitHub MCP server runs **in-process** (spawned subprocess) inside the same Cloud Run container.
- Start with **Cloud Run concurrency = 1** until you’ve validated MCP stdio behavior under concurrent requests.
- If you enable the **ADK web UI**, note ADK’s guidance that it’s **development-oriented**. For a hackathon, that’s usually OK; treat it as temporary and disable/private it after judging.

## Concrete deployment steps (Cloud Run + ADK UI enabled)

These steps use **Cloud Run + Dockerfile** so we can bundle the `github-mcp-server` binary and still serve the ADK UI.

### 0) Prereqs

- `gcloud` installed and authenticated
- A GCP project + region chosen:

```bash
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="us-central1"
gcloud config set project "$GOOGLE_CLOUD_PROJECT"
```

Enable required APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com
```

### 1) Prepare the Cloud Run entrypoint (serves ADK UI + API)

Copy the scaffold to repo root (Cloud Run build context expects these at the root):

```bash
cp deploy/cloudrun/main.py ./main.py
cp deploy/cloudrun/requirements.txt ./requirements.txt
cp deploy/cloudrun/Dockerfile ./Dockerfile
```

### 2) Point the Dockerfile at your Linux `github-mcp-server`

Edit `Dockerfile` and replace the placeholder value for `GITHUB_MCP_SERVER_URL` with the URL to the Linux `github-mcp-server` artifact you want to run in production.

### 3) Create secrets

Create a secret for your GitHub fine-grained PAT:

```bash
echo -n "YOUR_GITHUB_PAT" | gcloud secrets create GITHUB_PERSONAL_ACCESS_TOKEN --data-file=-
```

Model auth (choose one):

- **AI Studio**:

```bash
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
```

- **Vertex AI**: no API key secret required (use runtime env vars + Cloud Run service account permissions).

### 4) Deploy to Cloud Run (web UI enabled, shareable link)

Deploy from source:

```bash
gcloud run deploy swarmhq \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --allow-unauthenticated \
  --concurrency 1 \
  --min-instances 1 \
  --timeout 120 \
  --set-secrets "GITHUB_PERSONAL_ACCESS_TOKEN=GITHUB_PERSONAL_ACCESS_TOKEN:latest" \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --set-env-vars "ADK_WITH_UI=true,SWARMHQ_ORG_OWNER=YOUR_GITHUB_ORG,GOOGLE_GENAI_USE_VERTEXAI=false"
```

If using **Vertex AI**, replace the model-related env vars with:

- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION`

If your service account can’t read secrets yet, grant it `roles/secretmanager.secretAccessor` on the secrets you created.

### 5) What to share with evaluators

- Open the **service URL** in a browser (the ADK UI should load when `ADK_WITH_UI=true`).
- If you need a quick health/debug check:
  - `GET /list-apps`
  - `POST /run`

## Secrets + config (Secret Manager recommended)

Store these in Secret Manager and inject them as env vars:

- `GITHUB_PERSONAL_ACCESS_TOKEN` (fine-grained PAT; service-user account)
- Model auth (choose one):
  - Vertex: `GOOGLE_GENAI_USE_VERTEXAI=True` plus `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
  - or AI Studio: `GOOGLE_API_KEY`

Non-secret env vars:

- `SWARMHQ_ORG_OWNER` (your prod org)
- `GITHUB_MCP_COMMAND` (path to the MCP binary inside the container)
- `ADK_WITH_UI=true` (serve the ADK web UI)

## PAT permissions checklist (fine-grained PAT)

Create a PAT owned by a dedicated GitHub user (a “service user”), scoped to the org.

Minimum permissions for SwarmHQ’s current toolsets:

- **Organization**:
  - **Projects**: Read/Write (Projects v2)
  - **Members**: Read (optional; improves context)
- **Repository** (for the repo(s) you want to analyze):
  - **Issues**: Read/Write
  - **Contents**: Read
  - **Metadata**: Read

## Containerization approach

Cloud Run needs an HTTP server. ADK can be hosted via a FastAPI app (per ADK docs).

This repo includes a copy-pasteable Cloud Run scaffold here:

- `deploy/cloudrun/`

It contains:

- `deploy/cloudrun/main.py`: FastAPI app using ADK’s `get_fast_api_app()`, binds to `$PORT`
- `deploy/cloudrun/Dockerfile`: builds an image and installs `github-mcp-server` into `/app/bin/`
- `deploy/cloudrun/requirements.txt`: runtime deps

### How to use the scaffold

Option A (recommended): copy those three files to repo root before deploy:

- `deploy/cloudrun/main.py` → `./main.py`
- `deploy/cloudrun/Dockerfile` → `./Dockerfile`
- `deploy/cloudrun/requirements.txt` → `./requirements.txt`

Then deploy:

```bash
gcloud run deploy swarmhq \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --allow-unauthenticated \
  --concurrency 1
```

Set `ADK_WITH_UI=true` on the Cloud Run service so the chat UI is served.

Option B: keep scaffold in-place and use a separate build context (more advanced).

## Runtime validation checklist

After deploy:

- `GET /list-apps` returns your ADK app list
- `POST /run` can:
  - list org Projects (if you’re using Projects in the demo)
  - read Issues in the scoped org
  - (PM path) create/update an Issue when explicitly asked

## What evaluators should open

- **Web UI**: open the **service base URL** in the browser (the UI should load when `ADK_WITH_UI=true`).
- **API reference endpoints** (useful if UI isn’t loading): `GET /list-apps`, `POST /run`.

## Observability + safety defaults

Recommended Cloud Run settings for first production cut:

- **min instances**: 1 (reduces cold start + avoids first-call surprises with MCP startup)
- **concurrency**: 1 (until proven safe)
- **timeout**: 60–120s (depending on your model/tool latency)
- **CPU**: keep default; consider “CPU always allocated” only if you see startup thrash

## Security notes

- Keep `SWARMHQ_ORG_OWNER` locked to your intended org (it’s enforced again in `swarm_hq_agent/guardrails.py`).
- Treat the PAT as a production secret; rotate on any suspicion.
- For a hackathon share link, `--allow-unauthenticated` is simplest; after judging, switch to private or delete the service.
