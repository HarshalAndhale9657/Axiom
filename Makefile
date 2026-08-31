.PHONY: help setup data train report test api web docker verify clean

help:            ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:           ## install Python + Node dependencies
	pip install -r requirements.txt
	npm --prefix web install

data:            ## generate the seeded synthetic COD dataset
	python -m src.data.generate_synthetic_cod --n 20000 --seed 42

train:           ## train + calibrate the model and freeze the operating point on val
	python -m src.model.train

report:          ## regenerate every published number (docs/evaluation.md + figures + JSON)
	python -m src.model.full_report

test:            ## run the test suite (leakage, economics and bounded-action guards)
	pytest -q

api:             ## run the FastAPI backend at http://127.0.0.1:8000
	uvicorn src.api.main:app --reload

web:             ## run the Next.js dashboard at http://localhost:3000
	npm --prefix web run dev

docker:          ## build the reproducible backend image (data + model built inside)
	docker build -t axiom .

verify: data train test report  ## rebuild everything from scratch and re-audit the claims
	python -m src.model.full_report --check
	@echo "verified: dataset, model, tests and every published number rebuilt from source"

clean:           ## remove generated data, models and reports
	rm -rf reports/ models/axiom_rto_model.joblib models/thresholds.json \
	       data/cod_orders.csv data/cod_orders_latents.csv data/features.csv
