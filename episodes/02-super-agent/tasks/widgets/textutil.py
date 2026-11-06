import re
import unicodedata


def slugify(text: str) -> str:
    """Turn a title into a URL slug: lowercase ASCII words joined by single dashes."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "-", text)
    return text.lstrip("-")
