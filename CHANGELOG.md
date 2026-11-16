# Changelog

All notable changes to HarnessProbe are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## [0.4.0] - 2026-11-16

### Fixed

- **The bundled answer key was wrong.** `harnessprobe match` graded every
  completion against a table whose answers did not match its own problem
  statements: for the 22 statements kept from the previous set, 14 stored
  answers were provably wrong (e.g. the sum of primes below 20 was stored as 17
  instead of 77, the 100th term of 7, 12, 17, … as 6 instead of 502, and the
  divisor count of 10! as 12 instead of 270), and 6 more items had no integer
  answer in `[0, 999]` as worded. Live matched scores were therefore measured
  against invented answers. The set is now a 30-item AIME-format practice set
  (`AIME_PRACTICE_SUBSET`, ids `aime-practice-NN`), and
  `tests/test_bench_key.py` recomputes every answer independently, so a wrong
  key fails CI.
- **`repro --state` no longer substitutes a different profile.** The state file
  now records the profile key/path and the effective endpoint per row, and
  `repro` reloads exactly those. Previously a run started from
  `--models ./custom.yaml` was re-exported under the bundled vendor profile
  (different model, prompt, published score and endpoint) with no warning. A
  recorded profile that can no longer be loaded is now a clean exit 2, and the
  recorded stub/live mode is preserved instead of following the current
  environment.
- **Saved-state input errors are clean.** `report --state` and `repro --state`
  on an unrelated or truncated JSON document used to dump a `KeyError` /
  `JSONDecodeError` traceback; both now print a red message and exit 2.
- **Endpoint failure is visible and never scored as model performance.** At
  v0.3.0 failed completions were ungraded but invisible above the per-problem
  layer: a run in which every request failed printed a live `0.00 %` row, a
  "largest harness inflation" claim, and exited 0. `n_failed` is now carried on
  the run, the matrix row, the saved state, the CLI table and the HTML report;
  no harness-inflation claim is made for a row with failures; `match` exits 5
  after writing its artifacts when every completion for a model failed. The
  matched-score denominator is unchanged — failures still count as incorrect.

### Changed

- The bundled 30-problem set is documented as an AIME-format **practice set**,
  not the official AIME-2024 exam and not a reproduction of it. This corrects
  the provenance claim in the v0.1.0 notes; item ids are stable identifiers,
  not exam numbers.
- Version lockstep bump to 0.4.0 across `VERSION`, `pyproject.toml`,
  `harnessprobe/__init__.py`, and `web/site.json` (`meta.implementation_version`
  and `meta.content_version`).

## [0.3.0] - 2026-10-14

### Fixed

- **GitHub Release assets.** The release workflow built the wheel/sdist and
  checksums but only called `actions/upload-artifact` — the workflow artifact
  store — so nothing was ever attached to the GitHub Release object and v0.2.0
  shipped `release:success` with zero downloadable assets. A new `release` job
  now downloads the dist artifact and runs `gh release upload` (with a
  `gh release create --generate-notes` fallback), so every tag carries its
  wheel, sdist, and checksums.
- **Failed completions are never graded.** `run_match` caught adapter
  exceptions by writing `[runner error: …]` into the response and then
  extracting an integer from it — an endpoint error like "rate-limited, retry 6"
  could be graded as the correct answer to the problem whose expected answer is
  6. Failed completions now keep the error string for the audit trail but are
  recorded with `guessed=None`, `correct=False`, and a new `failed` flag (also
  exported in the repro package), so matched scores can no longer be inflated
  by endpoint failures.

### Added

- **`report --state` keeps the provenance trail.** `match` now persists each
  matrix row's harness assumptions (`model_name`, `reasoning_effort`,
  `temperature`, `max_tokens`, `stop_tokens`) and provenance entries into the
  saved state, and the `report` command rebuilds the "Per-profile provenance
  trail" section from it. Previously the documented saved-state re-render path
  silently dropped the audit trail. State files written before v0.3.0 still
  render — missing fields default to empty.

### Changed

- Version lockstep bump to 0.3.0 across `VERSION`, `pyproject.toml`,
  `harnessprobe/__init__.py`, and `web/site.json` `meta.implementation_version`.

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
- **Wheel build.** Removed a redundant `force-include` that duplicated
  `harnessprobe/profiles` into the wheel a second time and crashed hatchling
  builds (`A second file is being added ... deepseek_v4.yaml`) — the same
  failure that broke the v0.1.0 release artifacts. `packages =
  ["harnessprobe"]` already ships profiles and templates.

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
