from widgets.textutil import slugify
from widgets.money import format_cents
from widgets.durations import parse_duration
from widgets.inventory import Inventory
from widgets.csvio import read_rows


def test_slugify_simple():
    assert slugify("hello") == "hello"


def test_format_cents_simple():
    assert format_cents(1550) == "$15.50"


def test_parse_duration_simple():
    assert parse_duration("1h30m") == 5400


def test_inventory_add_remove():
    inv = Inventory()
    inv.add("a", 5)
    inv.remove("a", 2)
    assert inv.count("a") == 3


def test_read_rows_simple():
    assert read_rows("a,b\n1,2\n") == [{"a": "1", "b": "2"}]
