.PHONY: setup run test lint fmt docker

setup:
	pip install -e ".[dev,voice]"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --tb=short

lint:
	ruff check app/ tests/

fmt:
	ruff format app/ tests/

docker:
	docker compose up --build

seed-knowledge:
	python -m app.scripts.ingest_docs
