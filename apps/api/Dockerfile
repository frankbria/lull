# Lull API image (#55). uv builds a lean, locked venv; the prod compose runs uvicorn bound to
# loopback and the box's existing nginx + certbot front TLS.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# The project itself is installed (packages = src/lull_api), so src must be present for `uv sync`.
# alembic/ + alembic.ini ship in the image so migrations run from the same container.
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

EXPOSE 8000
# Default bind for a bridge-network run; the prod compose overrides host/port to loopback (the box
# uses host networking so uvicorn must pin 127.0.0.1).
CMD ["uv", "run", "--no-dev", "uvicorn", "lull_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
