FROM python:3.14-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies separately from application source so Docker
# can reuse this layer when only application code changes.
COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and configuration.
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

# Install the project itself.
RUN uv sync --frozen --no-dev

# Make the project's virtual environment the default Python environment.
ENV PATH="/app/.venv/bin:$PATH"
