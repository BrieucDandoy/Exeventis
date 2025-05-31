from datetime import datetime
from uuid import uuid4

from exeventis.aggregate import Aggregate
from exeventis.aggregate import Event
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


class Service(Application):
    pass


account_recorder = EventMemoryRecorder([Account], name="Account recorder")
dog_recorder = EventMemoryRecorder([Dog], name="dog recorder")
global_recorder = EventMemoryRecorder(name="global recorder")
service = Application(recorders=[account_recorder, dog_recorder, global_recorder])


class Account(Aggregate):
    def __init__(self, balance=0):
        self.balance = balance

    @event("deposit")
    def deposit(self, amount: int):
        self.balance += amount

    @event("withdraw")
    def withdraw(self, amount: int):
        self.balance -= amount


def test_event_capture():
    account = Account()
    account.deposit(100)
    account.withdraw(40)

    events = account.collect()
    assert len(events) == 2

    assert events[0].name == "deposit"
    assert events[0].event_kwargs == {"amount": 100}
    assert events[1].name == "withdraw"
    assert events[1].event_kwargs == {"amount": 40}


def test_mutation_from_events():
    account = None
    event1 = Event(
        name="deposit",
        type_="Account",
        event_kwargs={"amount": 100},
        version=1,
        originator_id=uuid4(),
    )
    event2 = Event(
        name="withdraw",
        type_="Account",
        event_kwargs={"amount": 20},
        version=2,
        originator_id=event1.originator_id,
    )

    account = event1.mutate(account)
    account = event2.mutate(account)

    assert account.balance == 80
    assert account._version == 2


def test_event_ordering_and_versioning():
    account = Account()
    account.deposit(50)
    account.withdraw(30)

    events = account.collect()

    assert events[0].version == 1
    assert events[1].version == 2


def test_state_rehydration_from_history():
    account = Account()
    account.deposit(10)
    account.withdraw(5)
    events = account.collect()

    # simulate storing and replaying
    state = None
    for _event in events:
        state = _event.mutate(state)

    assert isinstance(state, Account)
    assert state.balance == 5
    assert state._version == 2
