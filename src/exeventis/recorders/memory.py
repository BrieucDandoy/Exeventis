from collections import OrderedDict
from collections.abc import MutableMapping
from datetime import datetime
from typing import Any
from typing import Hashable
from typing import Iterator
from typing import Optional
from typing import Union
from uuid import UUID

from exeventis.abc import Recorder
from exeventis.aggregate import Aggregate
from exeventis.aggregate import Event
from exeventis.aggregate import Priority
from exeventis.exceptions import AggregateNotFoundError
from exeventis.reconstructor import StandartReconstructor


class EventMemoryRecorder(Recorder):
    """
    Basic in-memory recorder that stores events without limits.

    Stores events grouped by originator ID in an internal `EventMemory` instance.
    Uses a `Reconstructor` to rebuild aggregates from stored events on demand.

    Parameters
    ----------
    aggregates_types : list[type[Aggregate]], optional
        List of aggregate types this recorder supports (default is `[Aggregate]`).
    name : str, optional
        Optional name identifier for this recorder.
    """

    def __init__(self, aggregates_types=[Aggregate], name=None):
        super().__init__(aggregates_types, name)
        self.memory = EventMemory()
        self.reconstructor = StandartReconstructor()

    def save(self, event_list: list[Event]):
        """
        Stores a list of events in memory.

        Parameters
        ----------
        event_list : list[Event]
            List of events to store.
        """
        for event in event_list:
            self.memory.add(event)

    def get(self, originator_id: UUID):
        """
        Retrieves and reconstructs an aggregate by applying stored events.

        Parameters
        ----------
        originator_id : UUID
            The unique identifier of the aggregate.

        Returns
        -------
        Aggregate
            The reconstructed aggregate instance.

        Raises
        ------
        AggregateNotFoundError
            If no events exist for the given originator ID.
        """
        event_list = self.memory.get(originator_id)
        if event_list:
            return self.reconstructor.reconstruct(event_list)
        raise AggregateNotFoundError

    def __repr__(self):
        return self.memory.__repr__()


class EventMemory(MutableMapping):
    """
    In-memory store for events grouped by aggregate ID.

    This class implements a dictionary-like interface for managing lists of `Event` instances,
    each associated with an `originator_id` (UUID). It provides full `MutableMapping` support,
    allowing dictionary-like access and mutation.

    Attributes
    ----------
    data : dict[UUID, list[Event]]
        Internal mapping from aggregate UUIDs to lists of events.

    Methods
    -------
    add(event)
        Adds an event to the store under its `originator_id`. Creates the key if it doesn't exist.
    __getitem__(key)
        Retrieves the list of events associated with the given UUID.
    __setitem__(key, value)
        Sets the list of events for the given UUID.
    __delitem__(key)
        Deletes the entry associated with the given UUID.
    __iter__()
        Returns an iterator over the stored UUIDs.
    __len__()
        Returns the number of unique aggregate IDs stored.
    __repr__()
        Returns a string representation of the internal data dictionary.
    """

    def __init__(self):
        self.data: dict[UUID, list[Event]] = {}

    def add(self, event: Event) -> None:
        self.setdefault(event.originator_id, []).append(event)

    def __getitem__(self, key: UUID) -> list[Event]:
        return self.data[key]

    def __setitem__(self, key: UUID, value: list[Event]) -> None:
        self.data[key] = value

    def __delitem__(self, key: UUID) -> None:
        del self.data[key]

    def __iter__(self) -> Iterator[UUID]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self):
        return self.data.__repr__()


class LimitedOrderedDict:
    """
    A size-limited, insertion-order-preserving dictionary that stores lists of values per key.

    Internally uses an `OrderedDict` to maintain the order of key insertions and updates.
    Each key maps to a list of values. When a key is updated (i.e., a new value is added),
    that key is moved to the end of the order, marking it as recently used.

    The structure enforces a maximum total number of stored values (`max_size`). If this
    limit is reached, the least recently updated key and all of its values are evicted.

    Attributes
    ----------
    data : OrderedDict[Hashable, list[Any]]
        Internal storage preserving key insertion/update order.
    max_size : int
        Maximum total number of values allowed across all keys.
    current_size : int
        Tracks the current number of inserted values.

    Methods
    -------
    add(key, value)
        Adds a value to the list under the specified key and updates the key's recency.
    pop()
        Removes and returns the values associated with the least recently updated key.
    get(key, default=None)
        Returns the list of values for the given key, or `default` if key is not found.
    __contains__(key, value)
        Returns True if the value exists under the given key.
    __len__()
        Returns the number of keys in the dictionary.
    __iter__()
        Returns an iterator over the lists of values, in order of update recency.
    """

    def __init__(self, max_size: int = 5000):
        self.data: OrderedDict[Hashable, list[Any]] = OrderedDict()
        self.max_size = max_size
        self.current_size = 0

    def add(self, key: Hashable, value: Any):
        if key in self.data:
            value_list = self.data.pop(key)
        else:
            value_list = []
        value_list.append(value)
        self.data[key] = value_list
        if self.max_size == self.current_size + 1:
            self.pop()
        else:
            self.current_size += 1

    def get(self, key: Hashable, default: Optional[Any] = None):
        return self.data.get(key, default=default)

    def pop(self) -> list[Any]:
        _, obj = self.data.popitem(last=False)
        return obj

    def __contains__(self, key: Hashable, value: Any) -> bool:
        if key in self.data:
            return value in self.data[key]

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator:
        return iter(self.data.values())


class EventAggregateMemory(Recorder):
    """
    In-memory store for aggregates and their corresponding events, with replay capability.

    Aggregates and events are grouped by their originator ID and stored in limited-capacity,
    recency-aware dictionaries (`LimitedOrderedDict`). This allows efficient retrieval and
    reconstruction of an aggregate’s latest state by applying events on a snapshot.

    Attributes
    ----------
    snapshots : LimitedOrderedDict[UUID, list[Aggregate]]
        Stores snapshot versions of aggregates by their ID, with update-order tracking.
    events : LimitedOrderedDict[UUID, list[Event]]
        Stores events per aggregate by ID, with update-order tracking.

    Methods
    -------
    add_event(event)
        Stores an event under its originator ID.
    add_aggregate(aggregate)
        Stores a snapshot of the aggregate under its ID.
    get(originator_id, max_version=None, max_timestamp=None, default=None, priority=Priority.timestamp)
        Retrieves the most up-to-date state of an aggregate by applying events
        to its latest valid snapshot.
    """

    snapshots: LimitedOrderedDict[UUID, list[Aggregate]]
    events: LimitedOrderedDict[UUID, list[Event]]

    def __init__(self):
        self.snapshots: LimitedOrderedDict[UUID, list[Aggregate]] = LimitedOrderedDict()
        self.events: LimitedOrderedDict[UUID, list[Event]] = LimitedOrderedDict()
        self.reconstructor = StandartReconstructor()

    def add_event(self, event: Event):
        self.events.add(key=event.originator_id, value=event)

    def add_aggregate(self, aggregate: Aggregate):
        self.snapshots.add(key=aggregate._id, value=aggregate)

    def get(
        self,
        originator_id: UUID,
        max_version: Optional[int] = None,
        max_timestamp: Optional[datetime] = None,
        default: Optional[Any] = None,
        priority: Priority = Priority.timestamp,
    ) -> Union[Aggregate, Any]:
        """
        Reconstructs the current state of an aggregate by applying relevant events
        to its most recent valid snapshot.

        Filtering is applied to both snapshots and events using optional constraints
        on version and timestamp. Events newer than the selected snapshot are sorted
        and applied based on the chosen priority.

        Parameters
        ----------
        originator_id : UUID
            The unique identifier of the aggregate.
        max_version : int, optional
            Maximum version of the snapshot to consider.
        max_timestamp : datetime, optional
            Maximum timestamp of the snapshot to consider.
        default : Any, optional
            Value returned if no matching snapshot or event is found.
        priority : Priority, optional
            Determines how snapshots and events are ranked (default is Priority.timestamp).

        Returns
        -------
        Aggregate
            The aggregate with all filtered events applied to the selected snapshot.
            If no valid data is found, returns `default`.
        """
        snapshots: list[Aggregate] = self.snapshots.get(originator_id)
        events: list[Event] = self.events.get(originator_id)

        if not events and not snapshots:
            return default
        if max_version:
            snapshots = [snapshot for snapshot in snapshots if snapshot._version <= max_version]

        if max_timestamp:
            snapshots = [
                snapshot for snapshot in snapshots if snapshot._last_update_date <= max_timestamp
            ]
        aggregate = max(snapshots, key=priority.get_key(Aggregate))

        events = [event for event in events if event.version > aggregate._version]
        events = [event for event in events if event.timestamp > aggregate._last_update_date]

        return self.reconstructor.reconstruct(list_event=events, aggregate=aggregate)
