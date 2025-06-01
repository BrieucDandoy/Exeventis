from abc import ABC
from typing import Optional
from uuid import UUID

from exeventis.aggregate import Aggregate
from exeventis.reconstructor import Reconstructor


class EventRecorder(ABC):
    name: Optional[str] = None
    reconstructor: Reconstructor

    def __init__(
        self,
        aggregates_types: list[type[Aggregate]] = [Aggregate],
        name: Optional[str] = None,
    ):
        self.aggregates_types: list[type[Aggregate]] = aggregates_types
        self.name = name

    def save(self, aggregate: Aggregate):
        raise NotImplementedError

    def get(self, originator_id: UUID, **kwargs) -> Aggregate | None:
        raise NotImplementedError
