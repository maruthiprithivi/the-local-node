def read_rows(text: str) -> list[dict]:
    """Parse CSV text with a header row into a list of dicts (values are strings)."""
    lines = [line for line in text.splitlines() if line.strip()]
    header = lines[0].split(",")
    return [dict(zip(header, line.split(","))) for line in lines[1:]]
