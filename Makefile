.PHONY: build test smoke full all clean

build:
	docker compose build

test:
	docker compose run --rm sim python -m pytest -q

smoke:
	docker compose run --rm sim python -m openru_x6.cli run-suite --suite smoke --out results/smoke

full:
	docker compose run --rm sim python -m openru_x6.cli run-suite --suite full --out results/full

all:
	bash scripts/run_all.sh

clean:
	rm -rf results/smoke results/full .pytest_cache
