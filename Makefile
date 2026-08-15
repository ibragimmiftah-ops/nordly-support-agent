.PHONY: install seed test lint format run docker-build docker-up clean

install:
	pip install -e ".[dev]"

seed:
	python -m data.seed

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t nordly-support-agent .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f data/nordly.db
