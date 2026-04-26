# Contributing

Contributions are welcome. This project follows standard open-source practices.

## Getting Started

```bash
git clone <repo-url> && cd aviation-eval-harness
uv pip install -e ".[dev]"
```

## Development

- **Linting**: `ruff check .`
- **Tests**: `pytest`
- **Target Python**: 3.10+

## Adding a New Eval

1. Create a directory under `evals/` (e.g., `evals/my_eval/`)
2. Implement `class MyEval(Eval)` with `run()` and `run_single()` methods
3. Create a JSONL dataset under `datasets/`
4. Register in `runners/run_eval.py:EVAL_REGISTRY`

## Adding a New Model Provider

1. Implement `class MyAdapter(ModelAdapter)` in `models/adapters.py`
2. Register in `create_adapter()` factory function

## Dataset Contributions

All evaluation data must be **fully synthetic**. Do not submit:

- Verbatim text from real ASRS reports or NTSB investigations
- Real pilot names, callsigns, or identifying information
- Real flight numbers from active operators
- Data from proprietary or restricted sources

Synthetic cases should follow realistic aviation patterns and use the schemas documented in `datasets/README.md`.

## Pull Requests

- Keep PRs focused on a single change
- Include tests for new functionality
- Run `ruff check .` and `pytest` before submitting
