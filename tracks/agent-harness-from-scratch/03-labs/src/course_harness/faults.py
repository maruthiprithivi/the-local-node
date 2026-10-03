"""Deliberately defective provider doubles for controller defense exercises.

These bypass the normal FakeProvider contract. They are never a default provider,
live adapter, or configuration choice. Use only synthetic replies in failure tests.
"""
from copy import deepcopy


class UncheckedFixtureProvider:
    def __init__(self, replies):
        self.replies = iter(deepcopy(list(replies)))

    def complete(self, messages, tools=()):
        return deepcopy(next(self.replies))
