from collections import OrderedDict
from collections.abc import MutableMapping
from typing import Iterator
from uuid import UUID

from exeventis.aggregate import Aggregate
from exeventis.aggregate import Event
from exeventis.exceptions import AggregateNotFoundError
from exeventis.reconstructor import Reconstructor
from exeventis.recorders.base import EventRecorder


class EventMemoryRecorder(EventRecorder):
    def __init__(self, aggregates_types=[Aggregate], name=None):
        super().__init__(aggregates_types, name)
        self.memory = EventMemory()
        self.reconstructor = Reconstructor()

    def save(self, event_list: list[Event]):
        for event in event_list:
            self.memory.add(event)

    def get(self, originator_id: UUID):
        event_list = self.memory.get(originator_id)
        if event_list:
            return self.reconstructor.reconstruct(event_list)
        raise AggregateNotFoundError

    def __repr__(self):
        return self.memory.__repr__()


class EventMemory(MutableMapping):
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


class LimitedEventMemory:
    def __init__(self, max_size: int = 5000):
        self.data: OrderedDict[UUID, list[Event]] = OrderedDict()
        self.max_size = max_size
        self.current_size = 0

    def add(self, event: Event):
        if event.originator_id in self.data:
            event_list = self.data.pop(event.originator_id)
        else:
            event_list = []
        event_list.append(event)
        self.data[event.originator_id] = event_list
        if self.max_size == self.current_size + 1:
            self.pop()
        else:
            self.current_size += 1

    def pop(self) -> list[Event]:
        _, obj = self.data.popitem(last=False)
        return obj

    def __contains__(self, event: Event) -> bool:
        if event.originator_id in self.data:
            return event in self.data[event.originator_id]

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data.values())
