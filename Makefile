# Convenience helper targets for local development (one-line, npm-style)
# Use: `make train-demo` to create venv, install deps, and run loader+training
#      `make predict-demo` to run the prediction smoke test using the created venv

.PHONY: train-demo predict-demo

train-demo:
	python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt && .venv/bin/python services/api/scripts/load_and_train.py

predict-demo:
	.venv/bin/python services/api/scripts/predict_example.py
