help:	## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build:	## Build package
	poetry build

publish_to_pypi:	## Publish package to https://pypi.org
	poetry publish

publish_to_testpypi:	## Publish package to https://test.pypi.org
	poetry publish --repository testpypi

set_up_dev_environment:	## Install dependencies and dev-dependencies specified in pyproject.toml
	poetry install

test:	## Run tests
	poetry run pytest --cov=src --cov-report term-missing
