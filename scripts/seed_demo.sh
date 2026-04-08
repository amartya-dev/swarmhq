#!/usr/bin/env bash
# Seeds the swarmhq-demo org with the tiny-blog repo, issues, and Project Health Agent demo scenarios.
set -e

ORG="swarmhq-demo"
REPO="tiny-blog"

echo "==> Checking org access..."
gh api orgs/$ORG > /dev/null

echo "==> Creating repo $ORG/$REPO..."
gh repo create "$ORG/$REPO" --private --description "Demo blog for SwarmHQ" 2>/dev/null || echo "    (repo already exists, continuing)"

echo "==> Seeding file structure..."
FILES=(
  "web/index.html:<html><body><h1>Tiny Blog</h1></body></html>"
  "web/post.html:<html><body><h1>Post</h1></body></html>"
  "web/js/editor.js:// post editor"
  "web/js/date_format.js:// date formatting"
  "api/server.py:# api server"
  "api/posts.py:# posts handler"
  "api/rss.py:# rss feed"
  "api/comments.py:# comments handler"
)
for entry in "${FILES[@]}"; do
  path="${entry%%:*}"
  content="${entry#*:}"
  gh api repos/$ORG/$REPO/contents/$path \
    --method PUT \
    --field message="seed: add $path" \
    --field content="$(echo -n "$content" | base64)" \
    --silent 2>/dev/null || echo "    (skipping $path — already exists)"
done

echo "==> Adding labels..."
LABELS=(
  "type/bug:d73a4a"
  "type/feature:0075ca"
  "type/chore:e4e669"
  "type/incident:b60205"
  "priority/p0:b60205"
  "priority/p1:e4e669"
  "priority/p2:0075ca"
  "priority/p3:cfd3d7"
  "area/web:c5def5"
  "area/api:bfd4f2"
  "area/editor:d4c5f9"
  "area/comments:f9d0c4"
  "area/rss:fef2c0"
  "needs-triage:ededed"
  "needs-repro:ededed"
  "blocked:e11d48"
  "customer-report:f9d0c4"
  "regression:d93f0b"
)
for entry in "${LABELS[@]}"; do
  name="${entry%%:*}"
  color="${entry#*:}"
  gh label create "$name" --color "$color" --repo "$ORG/$REPO" 2>/dev/null || true
done

echo "==> Creating base issues..."

gh issue create --repo "$ORG/$REPO" \
  --title "Publish date shows 'yesterday' for users outside UTC" \
  --body "Affects \`web/js/date_format.js\`. Timezone math is wrong for non-UTC users." \
  --label "type/bug,priority/p1,area/web,regression" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Draft posts are visible to anonymous users" \
  --body "Filtering/auth check missing in \`api/posts.py\`." \
  --label "type/bug,priority/p0,area/api,customer-report" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "RSS feed missing most recent posts when there are >20" \
  --body "Pagination/limit issue in \`api/rss.py\`." \
  --label "type/bug,priority/p2,area/rss,needs-triage" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Comment spam bypasses basic moderation" \
  --body "See \`api/comments.py\`." \
  --label "type/bug,priority/p2,area/comments,needs-repro" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Editor occasionally loses text when switching between preview/edit" \
  --body "State handling issue in \`web/js/editor.js\`." \
  --label "type/bug,priority/p3,area/editor,needs-repro" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Markdown preview in the post editor" \
  --body "Add live markdown preview to the editor." \
  --label "type/feature,priority/p1,area/editor" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Tags and tag pages" \
  --body "Support tagging posts and browsing by tag." \
  --label "type/feature,priority/p2,area/web" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Search posts by title" \
  --body "Add title search to the web UI." \
  --label "type/feature,priority/p2,area/web" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Basic comment moderation queue" \
  --body "Queue for reviewing flagged comments before publishing." \
  --label "type/feature,priority/p2,area/comments,blocked" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Image upload for posts" \
  --body "Allow authors to upload images when writing posts." \
  --label "type/feature,priority/p3,area/api,area/web" 2>/dev/null || true

gh issue create --repo "$ORG/$REPO" \
  --title "Add rate limiting for comment submission" \
  --body "Chore: add rate limiting middleware for comment endpoint." \
  --label "type/chore,priority/p2,area/comments" 2>/dev/null || true

echo "==> Creating Project Health Agent demo scenarios..."

# --- Stale PR scenario ---
echo "  -> Stale PR: creating branch and PR for auth refactor..."
# Create a branch with an old commit by pushing a file
DEFAULT_SHA=$(gh api repos/$ORG/$REPO/git/ref/heads/main --jq '.object.sha')
# Create the branch
gh api repos/$ORG/$REPO/git/refs \
  --method POST \
  --field ref="refs/heads/refactor/auth-module" \
  --field sha="$DEFAULT_SHA" \
  --silent 2>/dev/null || echo "    (branch already exists)"

# Add a commit to the branch
gh api repos/$ORG/$REPO/contents/api/auth.py \
  --method PUT \
  --field message="refactor: begin auth module restructure" \
  --field content="$(echo -n '# auth module - in progress' | base64)" \
  --field branch="refactor/auth-module" \
  --silent 2>/dev/null || echo "    (file already exists on branch)"

# Create the stale PR (linked to issue for "in progress" board scenario)
gh pr create --repo "$ORG/$REPO" \
  --title "Refactor auth module" \
  --body "Restructuring the auth module for better separation of concerns. Closes #2." \
  --head "refactor/auth-module" \
  --base "main" 2>/dev/null || echo "    (PR already exists)"

echo "  -> Stale in-progress issue: 'Add rate limiting' marked in-progress with no PR..."
# Issue #11 (rate limiting) will be left with no linked PR — board-vs-reality scenario

# --- Overloaded contributor scenario ---
echo "  -> Creating extra PRs to trigger contributor overload signal..."
for i in 2 3 4; do
  BRANCH="feature/extra-stub-$i"
  gh api repos/$ORG/$REPO/git/refs \
    --method POST \
    --field ref="refs/heads/$BRANCH" \
    --field sha="$DEFAULT_SHA" \
    --silent 2>/dev/null || echo "    (branch $BRANCH already exists)"

  gh api repos/$ORG/$REPO/contents/stubs/stub_$i.py \
    --method PUT \
    --field message="chore: stub $i" \
    --field content="$(echo -n "# stub $i" | base64)" \
    --field branch="$BRANCH" \
    --silent 2>/dev/null || true

  gh pr create --repo "$ORG/$REPO" \
    --title "Stub feature $i" \
    --body "Stub PR $i for demo." \
    --head "$BRANCH" \
    --base "main" 2>/dev/null || echo "    (PR $i already exists)"
done

echo ""
echo "==> Done. Demo org seeded:"
echo "    Repo:    https://github.com/$ORG/$REPO"
echo "    Issues:  https://github.com/$ORG/$REPO/issues"
echo "    PRs:     https://github.com/$ORG/$REPO/pulls"
echo ""
echo "    Next: assign the open PRs to the same contributor to trigger"
echo "    the overload signal, then ask the agent 'How is the auth refactor going?'"
