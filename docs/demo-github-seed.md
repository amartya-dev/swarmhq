# Demo GitHub seed state (tiny blog project)

This seed is designed to make SwarmHQ demos feel “real” while staying small enough to set up in ~20–30 minutes.

## Goal

- **One org**
- **One repo**: a tiny blog site (web + small API)
- **A small set of seeded Issues** that power:
  - progress/status answers (via issue state/labels)
  - feature planning
  - bug/problem scoping

## 1) Create a demo org

Create a separate org so you can safely grant a PAT and avoid mixing demo data with real work.

- **Org name (suggested)**: `swarmhq-demo`
- **Visibility**: Private (recommended) or Public (fine for demos)

## 2) Create the demo repo (single repo)

Create a repo in the org:

- **Repo name**: `tiny-blog`
- **Default branch**: `main`

Then add a tiny file structure that gives the code analyzer something to point at in bug-scope answers (keep it simple; stubs are fine):

Suggested minimal files:

- `web/index.html`
- `web/post.html`
- `web/js/editor.js`
- `web/js/date_format.js`
- `api/server.py`
- `api/posts.py`
- `api/rss.py`
- `api/comments.py`

You can keep the code trivial; the important part is that those paths exist so bug scoping can reference them consistently.

## 3) Add labels to `tiny-blog`

Create these labels in the `tiny-blog` repo:

- **Type**: `type/bug`, `type/feature`, `type/chore`, `type/incident`
- **Priority**: `priority/p0`, `priority/p1`, `priority/p2`, `priority/p3`
- **Area**: `area/web`, `area/api`, `area/editor`, `area/comments`, `area/rss`
- **Triage**: `needs-triage`, `needs-repro`, `blocked`, `customer-report`, `regression`
- **Release (optional)**: `release/v0.1-demo`, `release/v0.2-demo`

## 4) Create a small set of seeded issues (12 total)

Create the following issues in `tiny-blog`. For each issue, set the listed labels and choose an issue state (Open/Closed) that matches the “Status” intent.

### Bugs (5)

1) **Publish date shows “yesterday” for users outside UTC**

- Labels: `type/bug`, `priority/p1`, `area/web`, `regression`, `release/v0.1-demo`
- Suggested state: **Open**
- Seed detail: points at `web/js/date_format.js` (timezone math).

2) **Draft posts are visible to anonymous users**

- Labels: `type/bug`, `priority/p0`, `area/api`, `customer-report`, `release/v0.1-demo`
- Suggested state: **Open**
- Seed detail: points at `api/posts.py` (filtering/auth check).

3) **RSS feed missing the most recent posts when there are >20**

- Labels: `type/bug`, `priority/p2`, `area/rss`, `needs-triage`, `release/v0.2-demo`
- Suggested state: **Open**
- Seed detail: points at `api/rss.py` (pagination/limit).

4) **Comment spam bypasses basic moderation**

- Labels: `type/bug`, `priority/p2`, `area/comments`, `needs-repro`
- Suggested state: **Open**
- Seed detail: points at `api/comments.py`.

5) **Editor occasionally loses text when switching between preview/edit**

- Labels: `type/bug`, `priority/p3`, `area/editor`, `needs-repro`
- Suggested state: **Open**
- Seed detail: points at `web/js/editor.js` (state handling).

### Features (5)

6) **Markdown preview in the post editor**

- Labels: `type/feature`, `priority/p1`, `area/editor`, `release/v0.1-demo`
- Suggested state: **Open**

7) **Tags and tag pages**

- Labels: `type/feature`, `priority/p2`, `area/web`, `release/v0.2-demo`
- Suggested state: **Open**

8) **Search posts by title**

- Labels: `type/feature`, `priority/p2`, `area/web`
- Suggested state: **Open**

9) **Basic comment moderation queue**

- Labels: `type/feature`, `priority/p2`, `area/comments`, `blocked`
- Suggested state: **Open**

10) **Image upload for posts**

- Labels: `type/feature`, `priority/p3`, `area/api`, `area/web`
- Suggested state: **Open**

### Chores/Incidents (2)

11) **2026-04-01: Blog page intermittently returns 500 (postmortem + follow-ups)**

- Labels: `type/incident`, `priority/p0`, `area/api`
- Suggested state: **Closed** (so you can demo “recently resolved incident”)

12) **Add rate limiting for comment submission**

- Labels: `type/chore`, `priority/p2`, `area/comments`, `release/v0.2-demo`
- Suggested state: **Open**

## 5) Point SwarmHQ at the demo org

Set:

- `SWARMHQ_ORG_OWNER="swarmhq-demo"` (or whatever org you created)

See `docs/local-testing.md` for local runs and example prompts.

## Optional later: add a GitHub Project (Projects v2)

If/when you want richer “portfolio” demos (views, custom fields, planned vs in-progress), add a single org-level Project and put the 12 issues in it. The earlier version of this doc included a ready-made field list; ask and I’ll re-add it as a separate `docs/demo-github-project.md`.

---

## Project Health Agent demo scenarios

These scenarios trigger the Project Health Agent’s signals and produce the PM-vs-Risk disagreement that is the core demo moment. Set them up after the base seed above.

### 1) Stale PR scenario

Create a pull request in `tiny-blog`:

- **Title**: `Refactor auth module`
- **Branch**: `refactor/auth-module` (create with an initial commit, then make no further commits)
- **State**: Open
- **Opened**: backdate by setting the branch’s last commit to 10+ days ago (force-push an empty commit with `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` set)
- **Project board**: add the linked issue (“Refactor auth module”) to the board with status **In Progress**

This gives the PM agent something to report as “in progress” while the Project Health Agent flags the PR as stale (no commits in 10+ days).

### 2) Overloaded contributor scenario

Assign **4 or more open PRs** to the same demo contributor account (e.g., `demo-contributor-1`). Use existing open PRs or create additional stub PRs against `tiny-blog`. The Project Health Agent will flag this contributor as overloaded.

### 3) Board-vs-reality scenario

- Open issue: **”Add rate limiting for comment submission”** (issue #12 from the base seed) — mark it **In Progress** on the project board and assign it to `demo-contributor-1`.
- Do **not** create any commits, branches, or PRs linked to this issue.

When queried, the PM agent will report the issue as in progress. The Project Health Agent will find no associated code activity and flag it as a contradiction.

### 4) Scripted demo prompt

Use this prompt verbatim during the demo:

> “How is the auth refactor going?”

**Expected behavior:**

The Coordinator consults the PM agent (which reads the project board and reports the auth refactor as “in progress”) and the Project Health Agent (which checks PR activity and finds no commits for 10+ days). The Coordinator’s final response explicitly calls out the disagreement:

> “The project board shows the auth refactor as in progress, but the activity data shows the PR has had no new commits for 10+ days. These views disagree.”

This is the moment that demonstrates the system’s value over a plain project-board view.
