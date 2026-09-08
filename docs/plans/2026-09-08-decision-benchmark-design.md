# Decision comparison and benchmark design

Approved scope comes from the user's acceptance of the preceding proposal and explicit instruction to implement. Work is isolated in `feat/decision-benchmark`. No additional design approval is needed.

Goal: make three implementation routes comparable, repair misleading review behavior, and measure against single-prompt and ordinary-sampling baselines. This is an experiment, not a validated decision engine.

Options considered: patch the existing ranking only (small but cannot test product value); add a GUI (more scope without evidence); retain the CLI and add structured routes plus a controlled benchmark (selected).

Each case gets one source-grounded task specification: original text, facts, preferences, hard constraints, unknowns and exact supporting quotes. Missing/invalid provenance fails extraction instead of silently dropping requirements. Original text remains available to the judge. The shared specification extraction is recorded separately in benchmark results and reused across arms. Baseline generation reads the original input; Stemcell generation reads the specification and three route instructions. A no-reset ablation feeds original input to Stemcell generation.

All arms produce the same structured candidate fields (scope, exclusions, steps, effort estimate and basis, risks, tradeoffs, choose-when). Single-prompt generates all candidates plus a comparative recommendation in one call. Sampling generates independent candidates without role prompts. Stemcell generates fastest-validation, lowest-maintenance and growth routes. Exact duplicates are removed; semantic diversity remains a human measurement, never inferred from labels.

The common judge sees identical original input/specification and output fields, with generator route labels removed. Hard-constraint judgments are pass/fail/unknown, cite candidate text, and cover every extracted constraint. Failed generation is excluded; failed evaluation becomes unassessed with no score; violated constraints cannot be compensated by soft scores. Missing or unverifiable evidence is unknown. Scores are validated and treated as model opinions, never probabilities. The displayed comparison preserves route order and conditional choices instead of crowning a numeric winner. A top list remains available for backward-compatible export only, excluding failed/unknown/violating reviews.

Usage records include stage, model, logical call count, actual returned tokens, duration, errors and optional cost using user-provided per-model rates. Unknown usage/cost is null, not zero. Disable implicit SDK retries for transparent accounting; enforce a maximum logical-call budget and finite numeric config. Do not claim a hard dollar/token spending cap. Model-specific temperature and token-parameter options are explicit.

Benchmark output: private full results and source mapping, randomized anonymous review packs, an empty human rating form, and a report that distinguishes technical completion from user effectiveness. Simulated fixtures are labeled as such. No fabricated human ratings, real usage numbers or real-case claims. Human ratings capture preferred bundle/tie/neither, reading time, constraint misses, meaningful routes, edits and eventual adoption. Run order is randomized. Equal-cost studies require matching measured spend; raw default comparisons are descriptive only.

Validation: unit and CLI tests with fake clients for bad JSON, missing fields, score bounds, errors, constraint failures, configuration wiring, accounting, strategy isolation, blinding, report interpretation and input validation; offline ten-case smoke run; real-provider run only when a configured credential and case sources are available. No automatic remote publishing.
