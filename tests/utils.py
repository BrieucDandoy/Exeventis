from datetime import datetime

from exeventis.aggregate import Aggregate
from exeventis.aggregate import event
from exeventis.application import Application
from exeventis.recorders.memory import EventMemoryRecorder


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


account_recorder = EventMemoryRecorder([Account], name="Account recorder")
dog_recorder = EventMemoryRecorder([Dog], name="dog recorder")
global_recorder = EventMemoryRecorder(name="global recorder")
service = Application(recorders=[account_recorder, dog_recorder, global_recorder])
