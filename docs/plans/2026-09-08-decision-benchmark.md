# Decision Benchmark Implementation Plan

**Goal:** Deliver a reliable, comparable CLI experiment with three generation strategies and honest evaluation artifacts.

**Architecture:** Preserve the small Python package and existing four modules. Add strict data validation, an instrumented client, structured rendering and a benchmark harness; inject fake clients for offline verification. Keep original inputs and provenance throughout.

**Tech Stack:** Python 3.12 development environment (package supports 3.10+), existing OpenAI-compatible SDK, Click, PyYAML, Rich; pytest and Ruff for development.

1. Add schema/config validation and instrument `stemcell/llm.py`. Tests cover strict JSON, unknown usage, stage totals, failed calls, model rates and call budgets. Use an isolated venv and fetch SDK documentation with Context7.
2. Repair `modules/reset.py` and `modules/quality.py`. Retain source quotes and full context. Add regression tests proving review failure has no score, hard failures are excluded, custom dimensions work and constraints cannot disappear during judging.
3. Implement structured route generation in `modules/clone.py`, `modules/differentiate.py`, and `pipeline.py`. Add single-prompt and sampling arms and a no-reset option. Tests verify method inputs, three routes, duplicate handling and configuration wiring.
4. Implement readable Markdown/text comparison and JSON exports, then CLI options with validated counts and budgets. Use `click.testing.CliRunner` for offline command tests.
5. Add `benchmark.py`, ten explicitly synthetic cases and human review templates. Tests ensure equal evaluation inputs, separate shared costs, anonymous random mappings and no inferred human results.
6. Run offline smoke experiments, write the initial report, update README and config examples, run pytest and Ruff, and inspect the final diff. Commit locally at useful milestones; do not push.

The accepted user direction authorizes implementation in this session. Optional skill handoff/subagent workflows are not needed for this bounded implementation.
