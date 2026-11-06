import re

_PATTERN = re.compile(r"^(\d+)h(\d+)m$")


def parse_duration(text: str) -> int:
    """Parse a duration such as "1h30m", "2h", "45m", "90s" or "1h2m3s" into seconds."""
    m = _PATTERN.match(text.strip())
    if not m:
        raise ValueError(f"bad duration: {text!r}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60
