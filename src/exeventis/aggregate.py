from __future__ import annotations

import inspect
from datetime import datetime
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel

from exeventis.exceptions import NotAnAggregateError


class AggregateMeta(type):
    _event_function_registry = {}
    _class_registry = {}

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        """Add a double entry dictionnary with class name -> event_name to get the method back,
        and a class registery to get the class"""
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "Aggregate":
            # Collect event methods
            event_methods = {}
            for attr_name, attr_value in namespace.items():
                if callable(attr_value) and getattr(attr_value, "_is_event", False):
                    event_name = getattr(attr_value, "_event_name", None)
                    if event_name:
                        event_methods[event_name] = attr_value._original_func
            mcs._class_registry[cls.__qualname__] = cls
            mcs._event_function_registry[name] = event_methods

        return cls

    def __call__(cls, *args, **kwargs) -> Aggregate:
        instance: Aggregate = cls.__new__(cls, *args, **kwargs)
        instance._unsaved_event_list = []
        instance._version = 0
        instance._id = uuid4()
        cls.__init__(instance, *args, **kwargs)
        return instance


class Aggregate(metaclass=AggregateMeta):
    _unsaved_event_list: list
    _version: int
    _id: UUID

    def collect(self) -> list[Event]:
        output = self._unsaved_event_list
        self._unsaved_event_list = []
        return output

    def __repr__(self):
        return f"{self._id},{self._version}"

    def __eq__(self, other: Aggregate):
        if isinstance(other, self.__class__) and self.__dict__ == other.__dict__:
            return True
        return False


def event(event_name):
    def event_decorator(method):
        def wrapper(self, *args, **kwargs):
            if not isinstance(self, Aggregate):
                raise NotAnAggregateError("Object must be an instance of Aggregate")

            sig = inspect.signature(method)
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            arg_dict = dict(bound.arguments)
            arg_dict.pop("self")
            try:
                timestamp = arg_dict.pop("timestamp")
            except KeyError:
                timestamp = datetime.now()
            self._version += 1
            new_event = Event(
                name=event_name,
                # get the class of the method
                type_=".".join(method.__qualname__.split(".")[:-1]),
                timestamp=timestamp,
                originator_id=self._id,
                event_kwargs=arg_dict,
                version=self._version,
            )
            self._unsaved_event_list.append(new_event)
            return method(self, *args, **kwargs)

        wrapper._is_event = True
        wrapper._event_name = event_name
        wrapper._original_func = method
        return wrapper

    return event_decorator


class Event(BaseModel):
    name: str
    type_: str
    event_kwargs: dict
    timestamp: datetime
    version: int
    originator_id: UUID

    def mutate(self, aggregate: Aggregate | None):
        func = AggregateMeta._event_function_registry[self.type_][self.name]
        if aggregate:
            func(aggregate, **self.event_kwargs)
            aggregate._version = self.version
            return aggregate
        aggregate_class: type[Aggregate] = AggregateMeta._class_registry[self.type_]
        # temporaly replace the init with the init without decorator to not trigger an event
        original_init = aggregate_class.__init__
        aggregate_class.__init__ = func
        instance = AggregateMeta.__call__(aggregate_class, **self.event_kwargs)
        instance._id = self.originator_id
        aggregate_class.__init__ = original_init
        instance._version = self.version
        return instance
