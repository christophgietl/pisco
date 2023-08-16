import invoke


@invoke.tasks.task
def run_git_hooks(c: invoke.context.Context) -> None:
    """Run git hooks on all files."""
    c.run("poetry run pre-commit run --all-files")


@invoke.tasks.task
def set_up_git_hooks(c: invoke.context.Context) -> None:
    """Install git hooks for testing, formatting and linting."""
    c.run("poetry run pre-commit install")
