# Convenience helper targets for local development
# Quick refs:
# - make run-api          # start FastAPI locally (http://localhost:8000)
# - make train-global     # train global categorizer from CSVs under data/
# - make predict          # call API to predict a category (set M and D)
# - make ingest           # upload sample CSV and upsert insights
# - make insights         # list insights for USER

.PHONY: install run-api train-demo predict-demo train train-global predict ingest insights goals-create goals-list

API ?= http://localhost:8000
USER ?= u_demo
CSV  ?= data/samples/transactions_u_unlabeled1_2024_2025_unlabeled.csv
M    ?= P&G
D    ?= shopping

# create venv and install project Python requirements
install:
	python3 -m venv .venv || true
	.venv/bin/pip install -U pip setuptools wheel
	.venv/bin/pip install -r services/api/requirements.txt

run-api: install
	cd services/api && ../.venv/bin/uvicorn app.main:app --reload

train-demo:
	python3 -m venv .venv && .venv/bin/pip install -r services/api/requirements.txt && .venv/bin/python services/api/scripts/load_and_train.py

predict-demo:
	.venv/bin/python services/api/scripts/predict_example.py

# Train all CSVs under data/training using the project's venv python
train: install
	.venv/bin/python services/api/scripts/train_from_folder.py data/training

# Train global categorizer from CSVs under data/training (falls back to samples)
train-global: install
	cd services/api && .venv/bin/python -c "from app.ai_categorizer import train_global; from pprint import pprint; print('Training global categorizer (min_per_class=5)...'); info = train_global(min_per_class=5); pprint(info)"

# Predict category via API using current USER, merchant (M) and description (D)
predict:
	@echo 'Predicting for USER=$(USER) merchant="$(M)" desc="$(D)" via $(API)'
	curl -sS -X POST $(API)/ai/categorizer/predict \
	  -H 'Content-Type: application/json' \
	  -d '{"user_id":"$(USER)","merchant":"$(M)","description":"$(D)","top_k":3}' | jq .

# Upload CSV and generate insights for USER (stateless auth header)
ingest:
	@echo 'Uploading $(CSV) for USER=$(USER) to $(API)'
	curl -sS -X POST $(API)/ingest/csv/insights \
	  -H 'X-User-Id: $(USER)' \
	  -F file=@$(CSV) | jq .

# List insights for USER
insights:
	curl -sS $(API)/users/$(USER)/insights | jq .

# Create a sample goal for USER (adjust amount/date with AMT/DATE)
AMT ?= 3000
DATE ?= 2025-12-31
goals-create:
	curl -sS -X POST $(API)/goals \
	  -H 'Content-Type: application/json' \
	  -H 'X-User-Id: $(USER)' \
	  -d '{"name":"Save $'"$(AMT)"'","target_amount":$(AMT),"target_date":"$(DATE)"}' | jq .

goals-list:
	curl -sS $(API)/users/$(USER)/goals | jq .
