from typing import Optional
from uuid import UUID

from exeventis.domain import Aggregate
from exeventis.recorder_store import RecorderStore


class Application:
    def __init__(self, recorder_store: RecorderStore):
        self.recorders = recorder_store

    def save(self, aggregate: Aggregate):
        self.recorders.save(aggregate)

    def get(
        self,
        originator_id: UUID,
        recorder_name: Optional[str] = None,
        *args,
        **kwargs,
    ):
        self.recorders.get(originator_id, recorder_name, *args, **kwargs)
