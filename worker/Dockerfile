# Build context is the repo root (see docker-compose.yml) - worker imports
# agent-core, mcp-server, and retrieval directly at runtime (see
# worker/pipeline.py's sys.path bootstrap for the two hyphenated dirs), so
# their code needs to sit alongside worker/ inside the image with the same
# relative layout as the repo.
FROM python:3.13-slim

WORKDIR /app

COPY worker/requirements.txt worker/requirements.txt
COPY agent-core/requirements.txt agent-core/requirements.txt
COPY retrieval/requirements.txt retrieval/requirements.txt
COPY mcp-server/requirements.txt mcp-server/requirements.txt

# retrieval's sentence-transformers dependency pulls in torch; installed
# via the default PyPI index that resolves to a multi-GB CUDA build this
# CPU-only worker never uses. Installing the CPU wheel first satisfies
# that dependency before pip gets a chance to reach for the CUDA one.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r worker/requirements.txt

COPY worker worker
COPY agent-core agent-core
COPY mcp-server mcp-server
COPY retrieval retrieval

WORKDIR /app
CMD ["python", "-m", "worker.main"]
