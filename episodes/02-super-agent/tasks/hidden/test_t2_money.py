from widgets.money import format_cents
def test_padding_and_negatives():
    assert format_cents(5) == "$0.05"
    assert format_cents(100) == "$1.00"
    assert format_cents(1505) == "$15.05"
    assert format_cents(-250) == "-$2.50"
    assert format_cents(-5) == "-$0.05"
    assert format_cents(0) == "$0.00"
