# SQLDetector Qwen

Modular, non-destructive SQL injection detector.

## Installation
```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage
```bash
python sqldetector_qwen.py https://example.com --dry-run
```

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
