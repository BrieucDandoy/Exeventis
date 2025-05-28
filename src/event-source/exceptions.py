class EventSourcingError(Exception):
    pass


class NotAnAggregateError(EventSourcingError):
    pass
