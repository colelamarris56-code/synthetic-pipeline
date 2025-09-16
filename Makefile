.PHONY: db-audit db-review db-billing billing-api review-api dash check fmt lint test

DB := $(PG_DSN)

db-audit:
	psql "$(DB)" -f db/audit.sql

db-review:
	psql "$(DB)" -f db/review.sql

db-billing:
	psql "$(DB)" -f db/billing.sql

billing-api:
	uvicorn scripts.billing_api:app --host 127.0.0.1 --port 8890

review-api:
	uvicorn scripts.review_api:app --host 127.0.0.1 --port 8891

dash:
	streamlit run scripts/dashboard_app.py --server.address 127.0.0.1 --server.port 8501

fmt:
	black .
	ruff format .

lint:
	ruff .

test:
	pytest -q

check: fmt lint test
