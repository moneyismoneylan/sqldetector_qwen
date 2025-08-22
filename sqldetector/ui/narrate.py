import sys
from typing import Optional

try:  # pragma: no cover - optional dependency
    from rich.console import Console  # type: ignore
    _console: Optional[Console] = Console(stderr=True)
except Exception:  # pragma: no cover - if rich missing
    _console = None


class Narrator:
    """Ultra-lightweight runtime narration helper.

    The narrator emits short human readable messages during a run.  If the
    ``rich`` package is available output is styled; otherwise plain ``stderr``
    is used.  All helpers are no-ops when ``quiet`` is ``True``.
    """

    def __init__(self, lang: str = "tr", quiet: bool = False) -> None:
        self.lang = lang
        self.quiet = quiet
        self._translations = {
            "Hedef profili çıkarılıyor…": {"en": "Profiling target…"},
            "OpenAPI içe aktarılıyor…": {"en": "Importing OpenAPI…"},
            "Postman içe aktarılıyor…": {"en": "Importing Postman…"},
            "HAR içe aktarılıyor…": {"en": "Importing HAR…"},
            "WAF sinyali tespit edildi, stealth moduna iniliyor.": {"en": "Learning WAF normalization"},
        }

    def _emit(self, prefix: str, msg: str) -> None:
        if self.quiet:
            return
        text = f"{prefix} {self._translate(msg)}"
        if _console:
            _console.print(text)
        else:
            print(text, file=sys.stderr)

    def _translate(self, msg: str) -> str:
        if self.lang == "en":
            return self._translations.get(msg, {}).get("en", msg)
        return msg

    def step(self, msg: str) -> None:
        self._emit("[*]", msg)

    def note(self, msg: str) -> None:
        self._emit("[-]", msg)

    def ok(self, msg: str) -> None:
        self._emit("[+]", msg)

    def warn(self, msg: str) -> None:
        self._emit("[!]", msg)

    def fail(self, msg: str) -> None:
        self._emit("[x]", msg)
