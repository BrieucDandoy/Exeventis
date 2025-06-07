from datetime import datetime
from uuid import uuid4

from utils import Account
from utils import Dog

from exeventis.application import Application
from exeventis.domain import Event
from exeventis.recorders.memory import EventMemoryRecorder

account_recorder = EventMemoryRecorder([Account], name="Account recorder")
dog_recorder = EventMemoryRecorder([Dog], name="dog recorder")
global_recorder = EventMemoryRecorder(name="global recorder")
service = Application(recorders=[account_recorder, dog_recorder, global_recorder])


def test_event_capture():
    account: Account = Account("test")
    account.add(100)
    account.subtract(40)

    events = account.collect()
    assert len(events) == 3

    assert events[0].name == "creation"
    print(events[0])
    assert events[0].event_kwargs == {"name": "test"}
    assert events[1].name == "add"
    assert events[1].event_kwargs == {"amount": 100}
    assert events[2].name == "subtract"
    assert events[2].event_kwargs == {"amount": 40}


def test_mutation_from_events():
    account = None

    event0 = Event(
        name="creation",
        type_="Account",
        event_kwargs={"name": "test"},
        timestamp=datetime.now(),
        version=1,
        originator_id=uuid4(),
    )
    event1 = Event(
        name="add",
        type_="Account",
        event_kwargs={"amount": 100},
        timestamp=datetime.now(),
        version=2,
        originator_id=event0.originator_id,
    )
    event2 = Event(
        name="subtract",
        type_="Account",
        event_kwargs={"amount": 20},
        timestamp=datetime.now(),
        version=3,
        originator_id=event1.originator_id,
    )
    account: Account = event0.mutate(account)
    account: Account = event1.mutate(account)
    account: Account = event2.mutate(account)

    assert account.balance == 80
    assert account._version == 3


def test_event_ordering_and_versioning():
    account: Account = Account("test")
    account.add(50)
    account.subtract(30)

    events = account.collect()
    print(events)

    assert events[0].version == 1
    assert events[1].version == 2
    assert events[2].version == 3


def test_state_rehydration_from_history():
    account: Account = Account("test")
    account.add(10)
    account.subtract(5)
    events = account.collect()

    # simulate storing and replaying
    state = None
    for _event in events:
        state = _event.mutate(state)

    assert isinstance(state, Account)
    assert state.balance == 5
    assert state._version == 3


if __name__ == "__main__":
    test_event_capture()
