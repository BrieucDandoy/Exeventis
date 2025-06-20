from typing import Optional
from uuid import UUID

from exeventis.abc import Recorder
from exeventis.aggregate import Aggregate
from exeventis.exceptions import AggregateNotFoundError


class Application:
    def __init__(self, recorders: list[Recorder]):
        self.recorders = recorders

    def save(self, aggregate: Aggregate):
        event_list = aggregate.collect()
        for recorder in self.recorders:
            for aggregate_type in recorder.aggregates_types:
                if isinstance(aggregate, aggregate_type):
                    recorder.save(event_list)

    def get(
        self,
        originator_id: UUID,
        recorder: Optional[Recorder] = None,
        recorder_name: Optional[str] = None,
        recorder_class: Optional[type[Recorder]] = None,
        *args,
        **kwargs,
    ):
        if recorder:
            return recorder.get(originator_id, *args, **kwargs)

        for recorder in self.recorders:
            if (recorder_name and recorder.name == recorder_name) or (
                recorder_class and isinstance(recorder, recorder_class)
            ):
                return recorder.get(originator_id, *args, **kwargs)
            try:
                aggregate: Optional[Aggregate] = recorder.get(originator_id, *args, **kwargs)
            except AggregateNotFoundError:
                aggregate = None
            if aggregate:
                return aggregate
