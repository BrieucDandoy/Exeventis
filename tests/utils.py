from datetime import datetime

from exeventis.domain import Aggregate
from exeventis.domain import event


class Account(Aggregate):
    @event("creation")
    def __init__(self, name: str):
        self.name = name
        self.balance = 0

    @event("add")
    def add(self, amount: float, timestamp: datetime = datetime.now()):
        self.balance += amount

    @event("subtract")
    def subtract(self, amount: float, timestamp: datetime = datetime.now()):
        self.balance -= amount

    def __repr__(self):
        return f"{self.name}, {self.balance}"


class Dog(Aggregate):
    @event("birth")
    def __init__(self, name: str):
        self.name = name
        self.tricks = []

    @event("add_trick")
    def add_trick(self, trick: str):
        self.tricks.append(trick)

    @event("remove_trick")
    def remove_trick(self, trick: str):
        if trick in self.tricks:
            self.tricks.remove(trick)
