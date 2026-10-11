FROM ghcr.io/astral-sh/uv:0.13.0-alpine3.23

WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

COPY uv.lock pyproject.toml /app

RUN uv sync

COPY . /app

CMD ["uv", "run", "main.py"]