from typing import List
from typing import Optional
from uuid import UUID

from exeventis.abc import Recorder
from exeventis.domain import Aggregate
from exeventis.exceptions import AggregateNotFoundError
from exeventis.exceptions import RecorderSavingError


class RecorderStore:
    """
    Coordinates multiple Recorder instances for saving and retrieving aggregates.

    The `RecorderStore` manages a collection of Recorder instances, executes
    transactional save and rollback logic, and optionally uses a Reconstructor
    to rebuild aggregates from stored events.

    Attributes
    ----------
    recorders : dict[str, Recorder]
        A dictionary mapping recorder names to their instances.
    """

    def __init__(self, recorders: List[Recorder]):
        """
        Initialize the RecorderStore.

        Parameters
        ----------
        recorders : list of Recorder
            A list of recorder instances to manage.
        reconstructor : Reconstructor, optional
            A custom reconstructor. If not provided, `StandartReconstructor` is used.
        """
        self.recorders = {recorder.name: recorder for recorder in recorders}

    def save(self, aggregate: Aggregate):
        """
        Save an aggregate using all applicable recorders, in order of rank.

        This method attempts to persist the aggregate to each recorder that declares
        itself responsible for it. If any recorder fails during the save operation,
        rollbacks are attempted in reverse order to maintain consistency.

        Parameters
        ----------
        aggregate : Aggregate
            The aggregate to be saved.

        Raises
        ------
        RecorderSavingError
            If any recorder fails to save
        """
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
        """
        Retrieve an aggregate by its originator ID.

        If a specific recorder name is provided, that recorder is used directly.
        Otherwise, recorders are tried in ascending order of rank until one succeeds.

        Parameters
        ----------
        originator_id : UUID
            The UUID of the aggregate to retrieve.
        recorder_name : str, optional
            The name of a specific recorder to use.
        *args :
            Positional arguments passed to the recorder's `get()` method.
        **kwargs :
            Keyword arguments passed to the recorder's `get()` method.

        Returns
        -------
        Aggregate or None
            The retrieved aggregate, or None if not found.

        """
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
