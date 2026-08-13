**English** | [简体中文](./README.md)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
  <img src="./assets/hero-light.svg" width="880" alt="HarnessProbe — reverse-engineer vendor harness assumptions into a matched-score matrix">
</picture>

<p align="center"><sub>Reverse-engineer per-vendor eval-harness assumptions into a matched-score GapMatrix for 信创 procurement</sub></p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-0071E3" alt="license"></a>
  <a href="https://github.com/SuperMarioYL/harnessprobe/releases"><img src="https://img.shields.io/github/v/release/SuperMarioYL/harnessprobe?color=5E5CE6" alt="release"></a>
  <a href="https://github.com/SuperMarioYL/harnessprobe/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/SuperMarioYL/harnessprobe/test.yml?branch=main&label=tests&color=10A37F" alt="tests"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/matched--score-gapmatrix-5E5CE6" alt="matched-score">
  <img src="https://img.shields.io/badge/harness--fidelity-probe-10A37F" alt="harness-fidelity">
</p>

<p align="center"><b>DeepSeek V4 / Qwen3.8 / Kimi K3 each publish benchmark scores tied to unreleased eval-harness assumptions. HarnessProbe reverse-engineers them and runs the same benchmark subset under matched assumptions to produce a comparable matched-score gap.</b></p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/atlas-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/atlas-light.svg">
  <img src="./assets/atlas-light.svg" width="880" alt="HarnessProbe architecture: CLI to Profile+Runner to GapMatrix+Report">
</picture>

<h2><img src="https://api.iconify.design/tabler/bulb.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Why this exists</h2>

CN model vendors (DeepSeek, Qwen, Kimi) now ship benchmark scores tied to proprietary, unreleased "harness minimal mode" configs — DeepSeek V4 Flash 0731's 82.7% on Terminal-Bench was reported using a "DeepSeek Harness minimal mode" that has never been published. When three credible CN frontier models coexist and each score runs under different harness assumptions, **a three-way comparison under unmatched harnesses is meaningless**. 信创 procurement teams signing private-deployment contracts need apples-to-apples reproducible evidence, not vendor marketing numbers. HarnessProbe types up each vendor's system-prompt shape, tool-call template, stop-token policy, reasoning-effort, and temperature into a `HarnessProfile`, applies it to the same AIME subset, and outputs vendor-published vs matched-reproduced vs gap.

<h2><img src="https://api.iconify.design/tabler/rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Install & Quickstart</h2>

```bash
uv tool install harnessprobe          # or pip install harnessprobe
export DEEPSEEK_API_KEY=... DASHSCOPE_API_KEY=... MOONSHOT_API_KEY=...
harnessprobe match --models deepseek-v4,qwen3-8,kimi-k3 --bench aime
```

> With no API keys set, HarnessProbe transparently enters **stub mode** — producing deterministic, vendor-differentiated stand-in scores so the whole pipeline runs end-to-end (for CI / demos / tests), but the scores are not vendor-representative. Set the three keys to switch to live mode.

<details><summary>Sample output</summary>

```
                        GapMatrix — AIME (30 problems)
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━┓
┃ Vendor   ┃ Model             ┃ Published ┃ Matched ┃    Gap ┃ Correct ┃ Mode ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━┩
│ deepseek │ deepseek-v4-pro-… │     79.80 │   70.00 │  -9.80 │   21/30 │ stub │
│ kimi     │ kimi-k3-0813      │     75.50 │   53.33 │ -22.17 │   16/30 │ stub │
│ qwen     │ qwen3.8-0813      │     77.20 │   46.67 │ -30.53 │   14/30 │ stub │
└──────────┴───────────────────┴───────────┴─────────┴────────┴─────────┴──────┘

Largest harness inflation: qwen/qwen3.8-0813 — published 77.20, matched 46.67, gap -30.53 pts.
```

</details>

<h2><img src="https://api.iconify.design/tabler/terminal-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Usage</h2>

Five core subcommands cover the full chain from matched reproduction to RFP-evidence export:

```bash
# List bundled profiles (the moat: reverse-engineered per-vendor assumption sets)
harnessprobe profiles

# Core command: run three models on the same AIME subset, print the GapMatrix
harnessprobe match --models deepseek-v4,qwen3-8,kimi-k3 --bench aime --n 30

# All-in-one: match + HTML report + repro-pkg
harnessprobe match --models deepseek-v4,qwen3-8,kimi-k3 --n 30 \
  --html report.html --repro repro.zip

# Render the HTML report from a saved match state
harnessprobe report --state .harnessprobe-last.json --out report.html

# Export a verbatim-reproducible repro-pkg (profile + prompts + raw outputs)
harnessprobe repro --state .harnessprobe-last.json --out repro.zip

# Programmatic API: see examples/basic_usage.py
```

`match` is the main command: after running it writes a `.harnessprobe-last.json` state file that subsequent `report` / `repro` calls can read without re-running. `--base-url` points at a private vLLM / SGLang endpoint. Full CLI reference: `harnessprobe match --help`.

<h2><img src="https://api.iconify.design/tabler/photo.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Demo</h2>

![demo](assets/demo.gif)

10-minute happy path: `pip install` → `match` → `report` → `repro`. See [`docs/demo.tape`](docs/demo.tape) (vhs script, re-rendered by CI on demand).

<h2><img src="https://api.iconify.design/tabler/adjustments.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Configuration</h2>

HarnessProfiles are static YAML under `harnessprobe/profiles/`. Core fields:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `vendor` | str | — | `deepseek` / `qwen` / `kimi` |
| `model_name` | str | — | model string sent to the OpenAI-compatible endpoint |
| `system_prompt` | str | — | reverse-engineered minimal-mode system prompt |
| `reasoning_effort` | str\|null | null | `low`/`medium`/`high` — reasoning-model harness lever |
| `temperature` | float | 0.0 | eval harnesses typically use greedy decoding |
| `stop_tokens` | list[str] | `[]` | stop-token policy (reverse-engineered fingerprint) |
| `decoding` | dict | `{}` | top_p / presence_penalty / etc. |
| `provenance` | list[str] | `[]` | public lead sources (reddit / card / reverse) — audit trail |
| `published_score` | dict | `{}` | vendor-published scores (bench name → score) |
| `api_key_env` | str | — | canonical: `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `MOONSHOT_API_KEY` |
| `base_url` | str | — | OpenAI-compatible endpoint |

Environment variables (schema-smoke verified):

| Variable | Vendor | Default endpoint |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek | `https://api.deepseek.com/v1` |
| `DASHSCOPE_API_KEY` | Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `MOONSHOT_API_KEY` | Kimi | `https://api.moonshot.cn/v1` |

> Two vendor-internal harness fields (exact function-call schema shape, internal stop-token priority) are UNVERIFIED — profiles mark them as best-effort reverse-engineering, tunable via `harnessprobe profile edit` (m3).

<h2><img src="https://api.iconify.design/tabler/map-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Roadmap</h2>

- [x] **m1 — profile encoding**: `HarnessProfile` Pydantic schema; DeepSeek V4 seed profile; single-endpoint AIME run producing a matched score + gap
- [x] **m2 — match matrix**: Qwen3.8 / Kimi K3 profiles added; 3-vendor × GapMatrix; HTML report + repro-pkg export **(v0.1 release, current)**
- [ ] **m3 — profile editor**: interactive `harnessprobe profile edit` (probe endpoints, diff assumptions); private-endpoint probes; 信创 integrator custom-profile service
- [ ] **Future**: full Terminal-Bench 2.1 agent reproduction (v0.2 hook, needs terminal sandbox + agent loop); quarterly per-vendor Profile Pack subscription

<h2><img src="https://api.iconify.design/tabler/credit-card.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Pricing</h2>

HarnessProbe's commercialization aligns with the proprietary-data moat — **the free OSS runner is the trojan horse into 30+ 信创 orgs; the accumulated per-vendor reverse-engineered profile set is what they pay for**.

| Tier | What's included | Price |
|---|---|---|
| **OSS free** | runner + 3 seed profiles + AIME matrix + HTML report + repro-pkg | ¥0 (MIT) |
| **Profile Pack subscription** | quarterly-updated full per-vendor reverse-engineered assumption set (DeepSeek/Qwen/Kimi) + provenance + historical snapshots | ¥30k–80k / yr / integrator site license |
| **Custom profile probing** | private-endpoint probe + one custom profile reverse-engineering engagement (m3 scope) | ¥15–30k / engagement |
| **Enterprise license** | audited per-vendor matrix integrators cite in RFP responses | ¥50k–200k / yr / integrator |

First paid customer segment: **信创 integrators** (中国软件 / 太极 / 神州数码) — they're contractually liable for benchmark claims in RFPs and need defensible matched scores + a `repro-pkg` they can hand to 甲方 for verbatim re-run, which they can't derive themselves (the proprietary-data moat). Billing: WeChat Pay / corporate transfer + license-key (no hosted SaaS in v0.1). See `BUILD_SETUP_NEXT_STEPS.md`.

<h2><img src="https://api.iconify.design/tabler/license.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> License</h2>

[MIT](./LICENSE). Issues and PRs welcome at [GitHub Issues](https://github.com/SuperMarioYL/harnessprobe/issues).

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
