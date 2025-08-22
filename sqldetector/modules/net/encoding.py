"""Accept-Encoding adaptation helper."""

def choose(phase: str) -> str:
    """Return encoding value for given phase."""
    if phase == "crawl":
        return "gzip, deflate"
    return "identity"
