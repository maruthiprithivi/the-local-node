class InsufficientStock(Exception):
    """Raised when removing more units than are in stock."""


class Inventory:
    def __init__(self):
        self._stock = {}

    def add(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def remove(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        self._stock[sku] = self._stock.get(sku, 0) - qty

    def count(self, sku: str) -> int:
        return self._stock.get(sku, 0)
