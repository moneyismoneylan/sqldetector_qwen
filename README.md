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

## Configuration

Create a TOML config and pass with `--config`:

```toml
safe_mode = true
legal_ack = true
trace_dir = "traces"
```

Command line overrides are available, e.g. `--log-json --log-level DEBUG`.

`--legal-ack` is required to acknowledge responsible use. The tool refuses to run without it.

## Usage

```bash
sqldetector https://example.com/products --legal-ack --trace-dir traces
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
