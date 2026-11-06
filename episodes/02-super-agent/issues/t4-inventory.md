# Inventory.remove lets stock go negative

`widgets.inventory.Inventory.remove` should raise `InsufficientStock` when asked to take more units than are in stock, and it should leave the count unchanged.

Expected:
- After `add("a", 3)`, `remove("a", 5)` raises `InsufficientStock` and `count("a")` stays 3.
- `remove("missing", 1)` raises `InsufficientStock` and `count("missing")` stays 0.
- `remove("a", 3)` succeeds and `count("a")` becomes 0.
