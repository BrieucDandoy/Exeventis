from __future__ import annotations

import inspect
from datetime import datetime
from enum import Enum
from typing import Union
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel

from exeventis.exceptions import NotAnAggregateError


class AggregateMeta(type):
    """
    Metaclass responsible for managing event registration and instantiating Aggregate classes.

    Maintains two registries:
    - `_event_function_registry`: Maps class names to a dictionary of event names and their
      corresponding original (undecorated) methods.
    - `_class_registry`: Maps qualified class names to class objects, enabling dynamic
      reconstruction (e.g., during deserialization).

    Methods
    -------
    __new__(mcs, name, bases, namespace)
        Gathers all methods decorated with @event and registers them.

    __call__(cls, *args, **kwargs)
        Creates an instance of an Aggregate, initializing its core attributes.
    """

    _event_function_registry = {}
    _class_registry = {}

    def __new__(mcs, name: str, bases: tuple, namespace: dict):
        """
        Registers event-handling methods and the class itself for later retrieval.

        Parameters
        ----------
        name : str
            Name of the class being created.
        bases : tuple
            Base classes of the new class.
        namespace : dict
            Class attributes and methods.

        Returns
        -------
        type
            The newly constructed class.
        """
        """Add a double entry dictionnary with class name -> event_name to get the method back,
        and a class registery to get the class when saving in a database"""
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
        """
        Instantiates an Aggregate and initializes event tracking attributes.

        Returns
        -------
        Aggregate
            A new aggregate instance with initialized metadata.
        """
        instance: Aggregate = cls.__new__(cls, *args, **kwargs)
        instance._unsaved_event_list = []
        instance._version = 0
        instance._id = uuid4()
        cls.__init__(instance, *args, **kwargs)
        return instance


class Aggregate(metaclass=AggregateMeta):
    """
    Base class for all domain aggregates. Inherit from this class to create your own aggregate.

    Attributes
    ----------
    _unsaved_event_list : list
        List of Event objects that have occurred but are not yet persisted.
    _version : int
        The version number of the aggregate (incremented with each event).
    _last_update_date : datetime
        Timestamp of the most recent event applied to this aggregate.
    _id : UUID
        Unique identifier for the aggregate instance.

    Methods
    -------
    collect()
        Returns and clears the list of unsaved events.
    __repr__()
        Returns a string representation of the aggregate (ID and version).
    __eq__(other)
        Checks for deep equality between two aggregates of the same type.
    """

    _unsaved_event_list: list
    _version: int
    _last_update_date: datetime
    _id: UUID

    def collect(self) -> list[Event]:
        """
        Returns and clears the list of unsaved events that have occurred.

        Returns
        -------
        list[Event]
            A list of events that were recorded but not yet persisted.
        """
        output = self._unsaved_event_list
        self._unsaved_event_list = []
        return output

    def __repr__(self):
        return f"{self._id},{self._version}"

    def __eq__(self, other: Aggregate):
        """
        Compares two aggregate instances for equality based on their internal state.

        Parameters
        ----------
        other : Aggregate
            Another aggregate instance to compare with.

        Returns
        -------
        bool
            True if both instances are of the same type and have equal attributes.
        """
        if isinstance(other, self.__class__) and self.__dict__ == other.__dict__:
            return True
        return False


def event(event_name):
    """
    Decorator that marks a method as an event handler and automatically
    triggers the creation of an Event object when the method is called.

    This decorator should be used on instance methods of classes derived from
    `Aggregate`. When the method is invoked, it:
    - Verifies that `self` is an Aggregate instance
    - Captures method arguments and the current timestamp
    - Increments the aggregate version
    - Creates and appends an `Event` to the aggregate’s unsaved event list
    - Calls the original method

    Parameters
    ----------
    event_name : str
        The name of the event (e.g., "created", "updated") that will be associated
        with the method. This is used in the `Event` object generated by the decorator.

    Returns
    -------
    Callable
        A decorated method that automatically emits an Event when invoked.

    Raises
    ------
    NotAnAggregateError
        If the decorated method is called on an object that is not an instance of `Aggregate`.
    """

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
            self._last_update_date = timestamp
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
    """
    Represents an event that has occurred on an Aggregate.

    Attributes
    ----------
    name : str
        The name of the event (e.g., 'created', 'updated').
    type_ : str
        A string used to identify the Aggregate class associated with this event
        (used during initialization).
    event_kwargs : dict
        A dictionary of arguments required to apply the event to the aggregate.
    timestamp : datetime
        The time at which the event occurred.
    version : int
        The version number of the aggregate at the time of the event.
    originator_id : UUID
        The unique identifier of the aggregate that originated the event.
    """

    name: str
    type_: str
    event_kwargs: dict
    timestamp: datetime
    version: int
    originator_id: UUID

    def mutate(self, aggregate: Aggregate | None) -> Aggregate:
        """
        Applies the event to an aggregate without emitting a new event.

        If the aggregate is provided, the corresponding event function is applied
        to mutate the aggregate in-place. If the aggregate is None, the event is
        treated as an initialization event and used to construct a new instance.

        Parameters
        ----------
        aggregate : Aggregate or None
            The aggregate to mutate. If None, a new aggregate instance is created.

        Returns
        -------
        Aggregate
            The resulting aggregate after applying the event.
        """
        func = AggregateMeta._event_function_registry[self.type_][self.name]
        if aggregate:
            func(aggregate, **self.event_kwargs)
            aggregate._version = self.version
            return aggregate
        aggregate_class: type[Aggregate] = AggregateMeta._class_registry[self.type_]
        # Temporarily replace __init__ to avoid triggering events
        original_init = aggregate_class.__init__
        aggregate_class.__init__ = func
        instance = AggregateMeta.__call__(aggregate_class, **self.event_kwargs)
        instance._id = self.originator_id
        aggregate_class.__init__ = original_init
        instance._version = self.version
        return instance


class Priority(Enum):
    version = "version"
    timestamp = "timestamp"

    def get_key(self, cls: type[Union[Aggregate, Event]] = Aggregate):
        """
        Returns a key function for sorting based on priority and class type.

        The key function can be used with Python's built-in sorting and selection
        functions such as `sorted()`, `list.sort()`, `max()`, and `min()`. The sorting
        behavior depends on the selected priority strategy (version or timestamp) and
        whether the items are of type `Aggregate` or `Event`.

        Parameters
        ----------
        cls : type of {Aggregate, Event}, optional
            The class type of the items to be sorted. Defaults to Aggregate.

        Returns
        -------
        Callable
            A function that takes an instance of the specified class and returns
            a tuple used for comparison in sorting operations.

        Raises
        ------
        ValueError
            If the combination of class type and priority is not supported.
        """

        if issubclass(cls, Aggregate):
            if self is Priority.version:
                return lambda x: (x._version, x._last_update_date)
            elif self is Priority.timestamp:
                return lambda x: (x._last_update_date, x._version)
        elif issubclass(cls, Event):
            if self is Priority.version:
                return lambda x: (x.version, x.timestamp)
            elif self is Priority.timestamp:
                return lambda x: (x.timestamp, x.version)
        raise ValueError(f"Invalid combination: cls={cls}, priority={self}")
