FROM python:3.10-bullseye

WORKDIR /app

COPY pyproject.toml .
COPY poetry.lock .

RUN pip install poetry && poetry install --no-root

COPY . .

CMD ["poetry", "run", "uvicorn", "llm_reports.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

