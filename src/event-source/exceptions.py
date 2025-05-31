class EventSourcingError(Exception):
    pass


class NotAnAggregateError(EventSourcingError):
    pass


class ReconstructionError(EventSourcingError):
    pass


class AggregateNotFoundError(EventSourcingError):
    pass
