help:	## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build:	## Build package
	poetry build

lint:	## Run git hooks on all files
	poetry run pre-commit run --all-files

set_up_dev_environment:	## Install dependencies and dev-dependencies specified in pyproject.toml
	poetry install

set_up_pre_commit:	## Install git hooks for formatting and linting
	poetry run pre-commit install

test:	## Run tests
	poetry run pytest --cov=src --cov-report term-missing
