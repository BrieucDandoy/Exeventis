from typing import Optional

from exeventis.abc import Reconstructor
from exeventis.aggregate import Aggregate
from exeventis.aggregate import Event
from exeventis.aggregate import Priority
from exeventis.exceptions import ReconstructionError


class StandartReconstructor(Reconstructor):
    """
    Reconstructs an aggregate by applying a sequence of events in order.

    Events are sorted according to a priority key function before being
    applied to an existing or new aggregate instance.

    Parameters
    ----------
    priority : Priority, optional
        The priority used to sort events before reconstruction
        (default is `Priority.timestamp`).
    """

    def reconstruct(
        self,
        list_event: list[Event],
        aggregate: Optional[Aggregate] = None,
        priority: Optional[Priority] = None,
    ) -> Aggregate:
        """
        Applies a sorted list of events to build or update an aggregate.

        Parameters
        ----------
        list_event : list[Event]
            List of events to apply.
        aggregate : Aggregate or None, optional
            Existing aggregate to apply events to, or None to create a new one.
        priority : Priority, optional
            Overrides the default priority for sorting events.

        Returns
        -------
        Aggregate
            The aggregate after applying all events.

        Raises
        ------
        ReconstructionError
            If an error occurs during event application.
        """
        if priority:
            list_event.sort(key=priority.get_key(Event))
        else:
            list_event.sort(key=self.priority.get_key(Event))

        for event in list_event:
            try:
                aggregate = event.mutate(aggregate)
            except:  # noqa
                raise ReconstructionError
        return aggregate
