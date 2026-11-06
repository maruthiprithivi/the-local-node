import pytest
from widgets.inventory import Inventory, InsufficientStock
def test_remove_more_than_stock_raises_and_keeps_count():
    inv = Inventory(); inv.add("a", 3)
    with pytest.raises(InsufficientStock):
        inv.remove("a", 5)
    assert inv.count("a") == 3
    with pytest.raises(InsufficientStock):
        inv.remove("missing", 1)
    assert inv.count("missing") == 0
    inv.remove("a", 3); assert inv.count("a") == 0
