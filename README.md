# SQLDetector v3 (Qwen Entegre)

## Kurulum
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma
```
python sqldetector_qwen.py https://example.com ^
  --llm-path "C:\llm\qwen3-4b-q4_k_m.gguf" ^
  --system-prompt-file system.txt ^
  --rpm 180 --max-pages 1000 --json-out findings.json
```

## Notlar
- SYSTEM_PROMPT'u `system.txt` dosyasına yaz veya `SYSTEM_PROMPT` env değişkeni ile geçir.
- LLM path vermezsen araç LLM'siz fallback ile çalışır (heuristic payload).
- Araç OKUMA modunda çalışır; yıkıcı işlem yapmaz.
