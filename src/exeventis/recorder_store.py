from typing import List
from typing import Optional
from uuid import UUID

from exeventis.abc import Reconstructor
from exeventis.abc import Recorder
from exeventis.domain import Aggregate
from exeventis.exceptions import AggregateNotFoundError
from exeventis.exceptions import RecorderSavingError


class RecorderStore:
    reconstructor: Reconstructor

    def __init__(self, recorders: List[Recorder]):
        self.recorders = {recorder.name: recorder for recorder in recorders}

    def save(self, aggregate: Aggregate):
        recorder_list = sorted(
            [recorder for recorder in self.recorders.values() if recorder.is_recordable(aggregate)],
            key=lambda x: x.rank,
        )
        try:
            for recorder in recorder_list:
                recorder.save(aggregate)
        except Exception as e:
            for rec in recorder_list:
                try:
                    rec.rollback()
                except RuntimeError:
                    continue
            raise RecorderSavingError from e
        for recorder in recorder_list:
            recorder.commit()

    def get(
        self,
        originator_id: UUID,
        recorder_name: Optional[str] = None,
        *args,
        **kwargs,
    ) -> Optional[Aggregate]:
        if recorder_name:
            return self.recorders[recorder_name].get(originator_id, *args, **kwargs)

        recorder_list = sorted(self.recorders.values(), key=lambda x: x.rank)
        for recorder in recorder_list:
            try:
                aggregate: Optional[Aggregate] = recorder.get(originator_id, *args, **kwargs)
            except AggregateNotFoundError:
                aggregate = None
            if aggregate:
                return aggregate
        return None
