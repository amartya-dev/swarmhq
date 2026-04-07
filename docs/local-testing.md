# Local testing guide (SwarmHQ + GitHub seed)

This is the quickest path to verify the agent can:

- summarize current status
- plan a feature from seeded issues
- scope a bug and point to likely code areas

## Prereqs

- You created the demo org/repo/issues in `docs/demo-github-seed.md`
- You have a GitHub token that can read org Projects and read/write Issues (fine-grained PAT is ideal)

## 1) Configure env vars

Copy the template:

```bash
cp swarm_hq_agent/.env.example swarm_hq_agent/.env
```

Set at minimum:

- `GITHUB_PERSONAL_ACCESS_TOKEN=...`
- `SWARMHQ_ORG_OWNER=swarmhq-demo` (or your demo org)

Model auth: set **either** Vertex vars or `GOOGLE_API_KEY` (see `swarm_hq_agent/.env.example`).

## 2) Run locally

From repo root:

```bash
uv sync
adk run swarm_hq_agent
```

Or with the dev web UI:

```bash
adk web --port 8000
```

## 3) High-signal demo prompts

### Project progress/status

- “Are we on track for `v0.1-demo`? What’s blocked and what decisions are needed?”
- “Summarize status by release and call out anything at risk.”

### Feature planning

- “Plan the scope + milestones for **Enterprise SSO (SAML)** for v1.0. What’s in/out, risks, and next actions?”

### Bug scoping

- “Customer says: *‘Sign in with Google hangs forever’*. Scope impact, likely areas, hypotheses, and what info we need next.”
- “We see duplicate orders after webhook retries. What’s the likely root cause and the mitigation?”

## 4) What “good” looks like

- The agent stays **decision-oriented** (not tool talk).
- It can identify **blocked** items (via labels), and reference the seeded issues.
- For bug scoping, it should point to areas consistent with the suggested demo repo file layout:
  - `web/login.js`, `api/auth/sso.py`, `api/webhooks/orders.py`, `api/billing/invoice.py`, `web/analytics/timezone.js`, `infra/runbooks/db-failover.md`

## 5) Common failure modes

- **“owner not found” / empty results**: `SWARMHQ_ORG_OWNER` is wrong or PAT lacks access to the org.
- **Can read repos but not Projects**: PAT is missing org-level Projects permission.
- **Writes blocked unexpectedly**: you’re hitting the read-only toolset (code analyzer); ask explicitly to create/update issues/project items so the PM path is used.
