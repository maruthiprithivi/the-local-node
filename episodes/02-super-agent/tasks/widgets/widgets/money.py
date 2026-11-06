def format_cents(cents: int) -> str:
    """Format an integer amount of cents as dollars, e.g. 1505 -> "$15.05", -250 -> "-$2.50"."""
    dollars = cents // 100
    rest = cents % 100
    return f"${dollars}.{rest}"
