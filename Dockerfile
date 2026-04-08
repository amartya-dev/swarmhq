FROM python:3.14-slim

WORKDIR /app

# System deps (curl for downloading github-mcp-server)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add a non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

# Copy agent code into image
COPY . .

# Install github-mcp-server (Linux build) into /app/bin.
# Replace this placeholder URL with the correct release artifact for your environment.
ARG GITHUB_MCP_SERVER_URL="https://github.com/github/github-mcp-server/releases/download/v0.32.0/github-mcp-server_Linux_x86_64.tar.gz"
RUN mkdir -p /app/bin \
  && curl -L "$GITHUB_MCP_SERVER_URL" | tar -xz -C /app/bin \
  && chmod +x /app/bin/github-mcp-server \
  && chown -R appuser:appuser /app/bin

USER appuser

ENV GITHUB_MCP_COMMAND="/app/bin/github-mcp-server"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
