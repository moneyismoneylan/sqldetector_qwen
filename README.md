# SQLDetector Qwen

Modular, non-destructive SQL injection detector.

## Installation

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix
source venv/bin/activate
pip install -e .
```

`requirements.txt` lists optional legacy extras; the canonical dependency list lives in `pyproject.toml`.


> **Note:** The project targets Python 3.9+. On Python versions prior to
> 3.11 the standard library lacks `tomllib`; the package
> [`tomli`](https://pypi.org/project/tomli/) is used to provide equivalent TOML
> parsing.

## Configuration


Create a TOML config and pass with `--config`:

```toml
safe_mode = true
trace_dir = "traces"
# HTTP client tuning
timeout_connect = 5.0
timeout_read = 10.0
timeout_write = 10.0
timeout_pool = 5.0
max_connections = 100
max_keepalive_connections = 20
```

Command line overrides are available, e.g. `--log-json --log-level DEBUG`.

## Usage

```bash
sqldetector https://example.com/products --trace-dir traces
```

Trace files are stored in the specified directory and can be used for reruns or auditing.

### Progress and WAF handling

`pipeline.run` accepts an optional `progress` callback that receives completion
percentages.  This can be used to display progress bars or estimate remaining
time for a scan.  When the internal HTTP client detects Cloudflare-style WAF
blocking it automatically falls back to a `cloudscraper` session to retry the
request.

### Performance features

The detector ships with several tuning knobs and optimisations:

1. Adaptive per-host concurrency limits
2. Token bucket rate limiting
3. Dynamic hedge requests to reduce tail latency
4. Circuit breaker on repeated failures
5. Retry budget controls for network/server errors
6. P95-based hedging delay calculation
7. Progress callbacks for responsive UIs
8. `cloudscraper` fallback for WAF evasion
9. Compact JSON tracing to minimise I/O
10. Reuse of HTTP/2 connections for lower overhead

### FAST preset (low-spec)

For a fast, resource-friendly scan on constrained machines:

```
sqldetector https://target --preset fast
```

The preset enables trace sampling and compression, caps discovery depth and
test counts, and stops after the first finding. System resources are detected
to auto-tune connection limits and timeouts.

Configuration keys introduced with this preset include:

* `trace_sample_rate`, `trace_compress`
* `stop_after_first_finding`
* `max_forms_per_page`, `max_tests_per_form`
* `use_llm` (`auto`/`always`/`never`)
* `llm_cache_path`, `llm_cache_ttl_hours`
* `fingerprint_db`

The fast pipeline performs an ultra-cheap keyword prefilter and maintains a
fingerprint database to skip heavy tests for unchanged pages.

## Turbo knobs

Advanced users can enable additional performance features via command line
flags.  These are disabled by default and require explicit opt-in.

```
sqldetector https://t \
  --simhash --form-dedupe --range-fetch-kb 64 \
  --bandit ucb1 --bloom --cpu-target-pct 40
```

Notable flags:

* `--bandit {off,ucb1,thompson}` – payload family scheduler
* `--dns-cache-ttl SEC` and `--prewarm` – DNS caching and connection warming
* `--happy-eyeballs` – IPv6/IPv4 racing dialer
* `--range-fetch-kb N` – partial body fetches for large files
* `--simhash` / `--near-dup-th N` – near-duplicate page detection
* `--form-dedupe` – skip identical form schemas
* `--server-weighting` – bias payloads based on server fingerprints
* `--endpoint-budget-ms MS` – per-endpoint time limits
* `--bloom --bloom-bits N --bloom-ttl HOURS` – persistent skiplist
* `--cpu-target-pct PCT --cpu-pacer-min-rps N --cpu-pacer-max-rps N` – CPU aware pacer

## Architecture

```
sqldetector_qwen.py ─▶ planner.pipeline.run()
                          │
                          ├── core/
                          ├── discovery/
                          ├── detect/
                          ├── db/
                          ├── waf/
                          ├── payload/
                          ├── fuzz/
                          ├── auth/
                          └── report/
```
