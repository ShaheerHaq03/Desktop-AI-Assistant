# Contributing

Thanks for your interest in contributing!

## Getting Started
- Fork the repo and create your feature branch: `git checkout -b feature/my-feature`
- Create a virtualenv and install deps: `pip install -r requirements.txt`
- Run tests locally: `pytest -q`

## Development Guidelines
- Follow the safety model. New actions must integrate with `SafetyManager` and capabilities.
- Add tests for new functionality in `tests/`.
- Keep code readable; prefer descriptive names and early returns.
- Do not enable dangerous capabilities by default.

## Commit and PR
- Use clear commit messages.
- Open a PR with a descriptive title and fill in the PR template.
- Ensure CI is green.

## Code of Conduct
By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

