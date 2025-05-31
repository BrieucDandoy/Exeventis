from aggregate import Event
from exceptions import ReconstructionError


class Reconstructor:
    def __init__(self, priorities: dict[str, float] = {}):
        self.priorities = priorities

    def reconstruct(self, list_event: list[Event]):
        if self.priorities:
            sorted_keys = sorted(self.priorities, key=self.priorities.get, reverse=True)
            list_event = sorted(
                list_event,
                key=lambda event: tuple(getattr(event, attr) for attr in sorted_keys),
            )
        aggregate = None
        for event in list_event:
            try:
                aggregate = event.mutate(aggregate)
            except:
                raise ReconstructionError
        return aggregate
