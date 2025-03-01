FROM python:3.11-slim AS builder

WORKDIR /app
RUN pip install --upgrade pip
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[voice]" --prefix=/install

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/

RUN mkdir -p data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
