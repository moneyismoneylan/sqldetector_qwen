import os
import uuid
from typing import Optional


class OOBClient:
    """Very small helper for out-of-band validation."""

    def __init__(self) -> None:
        self.endpoint = os.getenv("SMART_OOB_URL")
        self.token = os.getenv("SMART_OOB_TOKEN")
        self.enabled = bool(self.endpoint)

    def register(self) -> Optional[str]:
        if not self.enabled:
            return None
        return str(uuid.uuid4())

    def check(self, nonce: str) -> bool:
        # In real usage this would query the OOB service.  Offline tests simply
        # assume no callback is observed.
        return False
