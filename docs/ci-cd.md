# CI/CD — SwarmHQ

All deployments to Cloud Run go through GitHub Actions. Merging to `main` is the only deploy trigger.

```
PR opened → test job (mocked GitHub tools) → merge to main → deploy job (real GCP)
```

---

## Pipeline overview

`.github/workflows/deploy.yml` has two jobs:

| Job | Triggers | What it does |
|-----|----------|--------------|
| `test` | every PR + push to `main` | Runs ADK eval suite with mocked GitHub tools. Only needs `GOOGLE_API_KEY`. |
| `deploy` | push to `main` only (after `test` passes) | Downloads Linux `github-mcp-server`, authenticates to GCP via WIF, runs `adk deploy cloud_run`. |

---

## Required GitHub Actions secrets

Push them once with the helper script (see below):

| Secret | Description |
|--------|-------------|
| `GOOGLE_API_KEY` | Gemini API key — used by test job (LLM calls) and optionally by deploy |
| `SWARMHQ_ORG_OWNER` | GitHub org name to scope all agent access (e.g. `swarmhq-demo`) |
| `GH_PAT` | Fine-grained GitHub PAT for the runtime MCP server (deploy job only) |
| `GCP_PROJECT` | GCP project ID |
| `GCP_REGION` | Cloud Run region (e.g. `us-central1`) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | Service account email used by WIF (deploy SA) |
| `RUNTIME_SA_EMAIL` | Service account email the Cloud Run service runs as |
| `CLOUDSQL_CONN_NAME` | Cloud SQL connection name (`project:region:instance`) |
| `CLOUDSQL_DB_PASSWORD` | Postgres password (stored in Secret Manager; fetched at deploy time) |

---

## Pushing secrets with `scripts/push_github_secrets.py`

```bash
# From your local .env (default)
python scripts/push_github_secrets.py --repo YOUR_ORG/swarmhq

# From GCP Secret Manager
python scripts/push_github_secrets.py \
  --source secretmanager \
  --project YOUR_GCP_PROJECT \
  --repo YOUR_ORG/swarmhq

# Push only specific keys
python scripts/push_github_secrets.py \
  --keys GH_PAT,GOOGLE_API_KEY \
  --repo YOUR_ORG/swarmhq
```

Requires `gh` CLI authenticated (`gh auth login`). For the `secretmanager` source, also requires `gcloud` authenticated with read access to Secret Manager.

---

## One-time GCP setup

### 1. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  sqladmin.googleapis.com \
  iamcredentials.googleapis.com
```

### 2. Create service accounts

```bash
export PROJECT="your-gcp-project"

# Deploy SA — used by the workflow to run adk deploy
gcloud iam service-accounts create swarmhq-deploy \
  --project "$PROJECT" \
  --display-name "SwarmHQ GitHub Actions deploy"

# Runtime SA — the identity Cloud Run runs as
gcloud iam service-accounts create swarmhq-run \
  --project "$PROJECT" \
  --display-name "SwarmHQ Cloud Run runtime"
```

### 3. Grant permissions

```bash
DEPLOY_SA="swarmhq-deploy@$PROJECT.iam.gserviceaccount.com"
RUNTIME_SA="swarmhq-run@$PROJECT.iam.gserviceaccount.com"

# Deploy SA needs to build and deploy Cloud Run services
for role in roles/run.admin roles/cloudbuild.builds.editor roles/storage.admin roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$DEPLOY_SA" --role "$role"
done

# Runtime SA needs secrets, Cloud SQL, and Vertex AI
for role in roles/secretmanager.secretAccessor roles/cloudsql.client roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:$RUNTIME_SA" --role "$role"
done
```

### 4. Configure Workload Identity Federation

```bash
REPO="YOUR_ORG/swarmhq"

gcloud iam workload-identity-pools create github-pool \
  --project "$PROJECT" \
  --location global \
  --display-name "GitHub Actions pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project "$PROJECT" \
  --location global \
  --workload-identity-pool github-pool \
  --display-name "GitHub OIDC provider" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri "https://token.actions.githubusercontent.com"

POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --project "$PROJECT" --location global --format "value(name)")

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --project "$PROJECT" \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${REPO}"

# The value for GCP_WORKLOAD_IDENTITY_PROVIDER secret:
echo "${POOL_ID}/providers/github-provider"
```

### 5. Create Cloud SQL + secrets

Refer to the deploy command in `.github/workflows/deploy.yml` for the required
Cloud SQL setup. At minimum:

```bash
gcloud sql instances create swarmhq-sessions \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create adk_sessions --instance=swarmhq-sessions
gcloud sql users create adk --instance=swarmhq-sessions --password="STRONG_PASSWORD"

# Store DB password in Secret Manager (deploy job reads it at runtime)
gcloud secrets create CLOUDSQL_DB_PASSWORD --replication-policy=automatic
echo -n "STRONG_PASSWORD" | gcloud secrets versions add CLOUDSQL_DB_PASSWORD --data-file=-

# Store GitHub PAT in Secret Manager (injected into Cloud Run at deploy time)
gcloud secrets create GITHUB_PERSONAL_ACCESS_TOKEN --replication-policy=automatic
echo -n "YOUR_GITHUB_PAT" | gcloud secrets versions add GITHUB_PERSONAL_ACCESS_TOKEN --data-file=-
```

---

## Running tests locally

```bash
# Mock GitHub tools — only needs GOOGLE_API_KEY
SWARMHQ_TEST_MODE=1 GOOGLE_API_KEY=your-key uv run pytest tests/ -v

# Against real GitHub (requires binary + PAT)
GOOGLE_API_KEY=your-key \
GITHUB_PERSONAL_ACCESS_TOKEN=your-pat \
uv run pytest tests/ -v
```

---

## Triggering a manual deploy

The deploy job only runs on pushes to `main`. To trigger without a code change:

```bash
git commit --allow-empty -m "chore: trigger deploy" && git push origin main
```

Or use the GitHub Actions UI: **Actions → Test and Deploy → Run workflow → main**.
