FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy metadata trước để Docker cache layer cài dependency khi source thay đổi.
COPY pyproject.toml requirements.txt README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

EXPOSE 8000

USER app

CMD ["fastapi", "run", "src/app/main.py", "--host", "0.0.0.0", "--port", "8000"]
