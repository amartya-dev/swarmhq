import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app


AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Persist to /tmp (writable on Cloud Run). Keep it simple for demos.
SESSION_SERVICE_URI = os.getenv(
    "ADK_SESSION_SERVICE_URI", "sqlite+aiosqlite:////tmp/sessions.db"
)

# Serve the dev UI only if explicitly enabled.
SERVE_WEB_INTERFACE = os.getenv("ADK_WITH_UI", "").lower() in {"1", "true", "yes"}

app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=["*"],
    web=SERVE_WEB_INTERFACE,
    auto_create_session=True,
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
