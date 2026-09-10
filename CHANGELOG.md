# Changelog

All notable changes to HarnessProbe are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## [0.2.0] - 2026-09-10

### Fixed

- **Deterministic stub mode across processes.** The stub adapter's
  correctness gate was keyed on Python's builtin `hash()`, which is
  salt-randomized per process, so every `harnessprobe match` invocation
  produced different GapMatrix scores despite the documented determinism
  promise, and `harnessprobe repro --state ...` could never replay a prior
  run's outputs verbatim. The gate (and the wrong-answer offset) is now
  derived from a stable `zlib.crc32` digest — same inputs, same scores, on
  every machine and every run. Live mode is unchanged.
- **Clean CLI error contracts for `match`.** An unknown `--bench` key (e.g.
  `--bench mmlu`) dumped a raw `ValueError` traceback with exit code 1; it now
  prints a clean red message naming the supported key and exits 2, matching
  the existing profile-error path. `--n 0` and negative `--n` (which silently
  ran 25 problems via list slicing) are now rejected with the same clean
  exit-2 error.

### Added

- **`harnessprobe profile show / validate / probe`** — the first slice of the
  profile-editor (m3) roadmap: inspect a decoded profile (fields, provenance,
  published scores, system prompt), validate a custom YAML profile against the
  `HarnessProfile` schema before a long run (exit 0/2), and probe an endpoint
  with a one-token live completion to verify key + base URL before matching
  (connectivity failure exits 4; missing key is an informational exit 0).

### Changed

- Version lockstep bump to 0.2.0 across `VERSION`, `pyproject.toml`,
  `harnessprobe/__init__.py`, and `web/site.json` `meta.implementation_version`,
  with a version-consistency test keeping them in sync.

## [0.1.0] - 2026-08-13

### Added

- Initial m2 release: typed `HarnessProfile` schema (stdlib YAML subset loader
  + Pydantic validation) with seed profiles for DeepSeek V4 / Qwen3.8 / Kimi K3.
- `harnessprobe match` — per-vendor matched-harness run over the bundled
  AIME-2024 30-problem subset, printing the vendor-published vs matched
  GapMatrix (rich table), with deterministic stub mode when no API keys are set.
- `harnessprobe report` — HTML matched-score report (jinja2) from saved state.
- `harnessprobe repro` — verbatim-reproducible zip export (profiles + prompts +
  raw outputs + manifest) for procurement due-diligence.
- OpenAI-compatible adapter (httpx) applying system prompt, stop tokens,
  temperature, max_tokens, decoding knobs, and reasoning-effort per vendor.
