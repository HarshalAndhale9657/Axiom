.PHONY: setup data api web test figures

## setup: install Python + Node dependencies
setup:
	pip install -r requirements.txt
	npm --prefix web install

## data: generate the synthetic COD dataset and train + calibrate the model
data:
	python -m src.data.generate_synthetic_cod --n 20000 --seed 42
	python -m src.model.train

## api: run the FastAPI backend at http://127.0.0.1:8000
api:
	uvicorn src.api.main:app --reload

## web: run the Next.js dashboard at http://localhost:3000
web:
	npm --prefix web run dev

## test: run the Python test suite
test:
	pytest -q

## figures: regenerate the evaluation figures into docs/figures
figures:
	python -m src.model.evaluation --plots
