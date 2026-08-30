.PHONY: install index run test

install: ## Install dependencies into the active Python environment
	@pip install -r ../scripts/requirements.txt

index: ## (Re)build the vector index from the documents in data/
	python scripts/build_index.py

run: ## Start the Streamlit app (http://localhost:8501)
	streamlit run streamlit_app.py

test: ## Run the test suite
	pytest
