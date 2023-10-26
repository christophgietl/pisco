# Contributing to Pisco

Thank you for considering contributing to Pisco!
The following section describes how to set up and use a development environment.

## Development environment

Pisco uses the following developer tools:

- [mypy](https://mypy.readthedocs.io) for static type checking
- [Poetry](https://python-poetry.org) for dependency management and packaging
- [pre-commit](https://pre-commit.com) for managing pre-commit and pre-push hooks
- [pytest](https://pytest.org) for unit testing

### Setup

Please follow these steps to set up your development environment:

1. Install Poetry if you have not already done so.
2. Clone the Pisco repository and `cd` into it.
3. Install Pisco and its (development) dependencies by running `poetry install`.
4. Set up the hooks by executing `poetry run pre-commit install`.
   The output should look something like this:
   ```plain
   pre-commit installed at .git/hooks/pre-commit
   pre-commit installed at .git/hooks/pre-push
   ```

### Usage

Start Pisco in your new development environment:
```shell
poetry run pisco Küche  # Replace 'Küche' with the name of your Sonos device.
```

Run unit tests:
```shell
poetry run pytest
```

Run static type checks:
```shell
poetry run mypy .
```

Run pre-commit hooks:
```shell
poetry run pre-commit run --all-files
```
