from datetime import datetime
from uuid import uuid4

from utils import Account

from exeventis.aggregate import Event


def test_event_capture():
    account: Account = Account()
    account.deposit(100)
    account.withdraw(40)

    events = account.collect()
    assert len(events) == 3

    assert events[0].name == "creation"
    assert events[0].event_kwargs == {"balance": 0}
    assert events[1].name == "deposit"
    assert events[1].event_kwargs == {"amount": 100}
    assert events[2].name == "withdraw"
    assert events[2].event_kwargs == {"amount": 40}


def test_mutation_from_events():
    account = None

    event0 = Event(
        name="creation",
        type_="Account",
        event_kwargs={},
        timestamp=datetime.now(),
        version=1,
        originator_id=uuid4(),
    )
    event1 = Event(
        name="deposit",
        type_="Account",
        event_kwargs={"amount": 100},
        timestamp=datetime.now(),
        version=2,
        originator_id=event0.originator_id,
    )
    event2 = Event(
        name="withdraw",
        type_="Account",
        event_kwargs={"amount": 20},
        timestamp=datetime.now(),
        version=3,
        originator_id=event1.originator_id,
    )
    account = event0.mutate(account)
    account = event1.mutate(account)
    account = event2.mutate(account)

    assert account.balance == 80
    assert account._version == 3


def test_event_ordering_and_versioning():
    account = Account()
    account.deposit(50)
    account.withdraw(30)

    events = account.collect()
    print(events)

    assert events[0].version == 1
    assert events[1].version == 2
    assert events[2].version == 3


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
    assert state._version == 3
