# Convenience helper targets for local development (one-line, npm-style)
# Use: `make train-demo` to create venv, install deps, and run loader+training
#      `make predict-demo` to run the prediction smoke test using the created venv

.PHONY: install train-demo predict-demo train

# create venv and install project Python requirements
install:
	python3 -m venv .venv || true
	.venv/bin/pip install -U pip setuptools wheel
	.venv/bin/pip install -r services/api/requirements.txt

train-demo:
	python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt && .venv/bin/python services/api/scripts/load_and_train.py

predict-demo:
	.venv/bin/python services/api/scripts/predict_example.py

# Train all CSVs under data/training using the project's venv python
train: install
	.venv/bin/python services/api/scripts/train_from_folder.py data/training
