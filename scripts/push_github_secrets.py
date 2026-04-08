"""
Push GitHub Actions repository secrets from a local .env file or from GCP
Secret Manager.

Requires:
  - `gh` CLI authenticated (gh auth login) — used to set secrets
  - `gcloud` CLI authenticated (only for --source secretmanager)

Usage:
  # From .env (default)
  python scripts/push_github_secrets.py --repo owner/repo

  # From GCP Secret Manager
  python scripts/push_github_secrets.py \\
      --source secretmanager \\
      --project my-gcp-project \\
      --repo owner/repo

  # Override which keys to push
  python scripts/push_github_secrets.py --keys GH_PAT,GOOGLE_API_KEY --repo owner/repo
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Default set of keys that CI needs (matches deploy.yml).
_DEFAULT_KEYS = ",".join(
    [
        "GH_PAT",
        "GOOGLE_API_KEY",
        "SWARMHQ_ORG_OWNER",
        "GCP_PROJECT",
        "GCP_REGION",
        "GCP_WORKLOAD_IDENTITY_PROVIDER",
        "GCP_SERVICE_ACCOUNT",
        "RUNTIME_SA_EMAIL",
        "CLOUDSQL_CONN_NAME",
        "CLOUDSQL_DB_PASSWORD",
    ]
)


def _parse_dotenv(path: Path) -> dict[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f".env file not found: {path}") from e

    out: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        out[key] = value
    return out


def _run(cmd: list[str], *, stdin_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _detect_repo() -> str | None:
    """Try to infer owner/repo from git remote origin."""
    r = _run(["git", "remote", "get-url", "origin"])
    if r.returncode != 0:
        return None
    url = r.stdout.strip()
    # Handle ssh (git@github.com:owner/repo.git) and https forms.
    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:").removesuffix(".git")
        return path
    if "github.com/" in url:
        path = url.split("github.com/", 1)[1].removesuffix(".git")
        return path
    return None


def _read_from_dotenv(keys: list[str], env_file: str | None) -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[1]
    candidates = (
        [Path(env_file)]
        if env_file
        else [repo_root / "swarm_hq_agent" / ".env", repo_root / ".env"]
    )
    env_path = next((p for p in candidates if p.exists()), None)
    if env_path is None:
        print(
            "No .env found. Create one at:\n"
            + "\n".join(f"  {p}" for p in candidates),
            file=sys.stderr,
        )
        sys.exit(2)
    env = _parse_dotenv(env_path)
    missing = [k for k in keys if k not in env or not env[k]]
    if missing:
        print(
            "Missing keys in .env (or empty): " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(2)
    return {k: env[k] for k in keys}


def _read_from_secret_manager(keys: list[str], project: str) -> dict[str, str]:
    if not project:
        print(
            "Missing --project (required for --source secretmanager).",
            file=sys.stderr,
        )
        sys.exit(2)
    values: dict[str, str] = {}
    for key in keys:
        r = _run(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                "latest",
                f"--secret={key}",
                f"--project={project}",
            ]
        )
        if r.returncode != 0:
            print(f"Failed to read secret '{key}' from Secret Manager:\n{r.stdout}", file=sys.stderr)
            sys.exit(2)
        values[key] = r.stdout.strip()
    return values


def _push_to_github(key: str, value: str, repo: str) -> None:
    r = _run(
        ["gh", "secret", "set", key, "--body", value, "--repo", repo],
    )
    if r.returncode != 0:
        raise RuntimeError(f"Failed to set GitHub secret '{key}':\n{r.stdout}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Push secrets to GitHub Actions from a local .env file or from "
            "GCP Secret Manager. Values are never printed."
        )
    )
    parser.add_argument(
        "--source",
        choices=["env", "secretmanager"],
        default="env",
        help="Where to read secret values from (default: env).",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Path to .env (default: swarm_hq_agent/.env then .env).",
    )
    parser.add_argument(
        "--project",
        default=os.getenv("GOOGLE_CLOUD_PROJECT"),
        help="GCP project ID (required for --source secretmanager).",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="GitHub repo as owner/repo (default: auto-detected from git remote).",
    )
    parser.add_argument(
        "--keys",
        default=_DEFAULT_KEYS,
        help="Comma-separated list of secret keys to push.",
    )
    args = parser.parse_args()

    repo = args.repo or _detect_repo()
    if not repo:
        print(
            "Could not detect repo. Pass --repo owner/repo explicitly.",
            file=sys.stderr,
        )
        return 2

    keys = [k.strip() for k in args.keys.split(",") if k.strip()]

    if args.source == "env":
        values = _read_from_dotenv(keys, args.env_file)
    else:
        values = _read_from_secret_manager(keys, args.project or "")

    for key in keys:
        _push_to_github(key, values[key], repo)
        print(f"Set secret: {key}")

    print(f"\nAll {len(keys)} secret(s) pushed to {repo}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
