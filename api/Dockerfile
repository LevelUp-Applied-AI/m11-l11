# Vendored from the M10 stack with M11 observability deps layered on.
# Build context: repo root (parent of api/).
# In docker-compose.yml:  build: { context: ., dockerfile: api/Dockerfile }
#
# This preserves package-relative imports (api/main.py: from .deps import ...).
# Running `uvicorn api.main:app` from /app loads the `api` package; running
# `uvicorn main:app` from /app/api would break the relative imports with
# `ImportError: attempted relative import with no known parent package`.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

# Install core dependencies and the specific pinned spaCy model via direct URL
RUN pip install fastapi uvicorn pydantic==2.6.0 weaviate-client neo4j spacy==3.7.4 prometheus-client pytest pytest-asyncio httpx && \
    pip install --no-cache-dir --timeout 300 --retries 5 https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

COPY api/ /app/api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]