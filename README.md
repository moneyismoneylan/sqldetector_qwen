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


> **Note:** The project targets Python 3.11+ where the standard library includes
> `tomllib` for reading TOML configuration.  If you are on an older Python
> release, install [`tomli`](https://pypi.org/project/tomli/) to provide the same
> functionality.

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
