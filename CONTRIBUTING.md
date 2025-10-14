# Contributing

1. Create an issue describing the change/bug.
2. Create a branch `feature/<brief-name>` off main.
3. Add tests for new preprocessing or model code.
4. Open a PR with description and link to issues. Use small, focused PRs.
5. CI will run pytest. Keep changes incremental.

Coding style:
- Python: Flake-compatible, docstrings for public functions.
- Tests: use pytest and small synthetic data arrays for speed.