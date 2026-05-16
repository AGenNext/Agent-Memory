# Contributing to Agent-Memory

Thank you for your interest in contributing to Agent-Memory.

## Development Setup

1. Fork the repository.
2. Clone your fork.
3. Install dependencies:

```bash
uv sync
```

4. Create a `.env` file:

```bash
OPENAI_API_KEY=your_api_key_here
```

5. Start SurrealDB.
6. Load sample data:

```bash
uv run python load.py
```

## Contribution Ideas

- New retrieval strategies
- Additional agent implementations
- Performance benchmarks
- Bug fixes
- Documentation improvements
- Sample datasets

## Pull Request Guidelines

- Keep pull requests focused and easy to review.
- Update documentation when behavior changes.
- Add tests where practical.
- Use clear commit messages.

## Reporting Issues

When opening an issue, please include:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details
- Relevant logs or screenshots

## Code Style

- Prefer readable, well-documented code.
- Keep functions small and focused.
- Add comments only where they improve understanding.

Thank you for helping improve Agent-Memory.
