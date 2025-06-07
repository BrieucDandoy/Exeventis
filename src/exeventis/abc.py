from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import List
from typing import Optional
from typing import Union
from uuid import UUID

from exeventis.domain import Aggregate
from exeventis.domain import Event
from exeventis.domain import Priority


class Recorder(ABC):
    """
    Abstract base class for recorders that store and retrieve aggregates and/or events.

    Attributes
    ----------
    aggregates_types : list[type[Aggregate]]
        List of aggregate classes supported by this recorder.
    name : str or None
        Optional name identifier for the recorder.
    reconstructor : Reconstructor
        The reconstructor instance used to rebuild aggregates from stored events.
    """

    name: Optional[str] = None
    reconstructor: Reconstructor
    rank: Union[float, int]

    def __init__(
        self,
        aggregates_types: list[type[Aggregate]] = [Aggregate],
        name: Optional[str] = None,
    ):
        self.aggregates_types: list[type[Aggregate]] = aggregates_types
        self.name = name

    @abstractmethod
    def save(self, aggregate: Aggregate):
        """
        Abstract method to save events.

        Parameters
        ----------
        aggregate : Aggregate
            The aggregate instance to save.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass

    @abstractmethod
    def get(self, originator_id: UUID, **kwargs) -> Optional[List[Event]]:
        """
        Abstract method to retrieve an aggregate by originator ID.

        Parameters
        ----------
        originator_id : UUID
            The unique identifier of the aggregate to retrieve.

        Returns
        -------
        Aggregate or None
            The retrieved aggregate or None if not found.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        pass

    def is_recordable(self, aggregate: Aggregate) -> bool:
        for cls in self.aggregates_types:
            if isinstance(aggregate, cls):
                return True
        return False


class Reconstructor(ABC):
    """
    Abstract base class for reconstructing an aggregate from a sequence of events.

    This class defines the interface for rebuilding or updating an aggregate by
    applying a list of domain events in a defined order.

    Attributes
    ----------
    priority : Priority
        The default sorting strategy used to order events before applying them.

    Methods
    -------
    reconstruct(list_event, aggregate=None, priority=None)
        Applies a list of events to an aggregate to reconstruct its state.
    """

    priority: Priority

    def __init__(self, priority: Priority = Priority.version):
        """
        Initialize the reconstructor with a default event sorting strategy.

        Parameters
        ----------
        prioritiy : Priority, optional
            The default priority used to sort events before applying them
            (default is Priority.timestamp).
        """
        self.priority = priority

    @abstractmethod
    def reconstruct(
        self,
        list_event: list[Event],
        aggregate: Optional[Aggregate] = None,
        priority: Optional[Priority] = None,
    ) -> Aggregate:
        """
        Applies a sequence of events to build or update an aggregate.

        Parameters
        ----------
        list_event : list of Event
            Events to apply in sequence.
        aggregate : Aggregate, optional
            Existing aggregate to update. If None, reconstruction starts from scratch.
        priority : Priority, optional
            Overrides the default priority for sorting events.

        Returns
        -------
        Aggregate
            The resulting aggregate after applying all applicable events.

        Raises
        ------
        NotImplementedError
            If the method is not implemented in a subclass.
        """
        pass


class Transcoder(ABC):
    """
    Abstract base class for data transcoders that serialize and deserialize specific types.

    Each transcoder defines how to encode a value of a specific class into a
    string representation and decode it back into its original type.

    Attributes
    ----------
    name : str
        A unique name identifying the transcoder (e.g., "__UUID__").
    _class : type
        The data type this transcoder handles (e.g., `UUID`, `datetime`).

    Methods
    -------
    encode(data: Any) -> str
        Converts a value of `_class` to a string.
    decode(encoded_data: dict) -> Any
        Converts a string back to a value of `_class`.
    """

    name: str
    _class: type

    def __init__(self, name: Optional[str], _class: Optional[type]):
        """
        Abstract base class for data transcoders that serialize and deserialize specific types.

        Each transcoder defines how to encode a value of a specific class into a
        string representation and decode it back into its original type.

        Attributes
        ----------
        name : str
            A unique name identifying the transcoder (e.g., "__UUID__").
        _class : type
            The data type this transcoder handles (e.g., `UUID`, `datetime`).

        Methods
        -------
        encode(data: Any) -> str
            Converts a value of `_class` to a string.
        decode(encoded_data: dict) -> Any
            Converts a string back to a value of `_class`.
        """
        if name:
            self.name = name
        if _class:
            self._class = _class

    @abstractmethod
    def encode(self, data: Any) -> str:
        """
        Encode a value to a string.

        Parameters
        ----------
        data : Any
            The value to encode.

        Returns
        -------
        str
            Encoded string representation of the value.
        """
        pass

    @abstractmethod
    def decode(self, encoded_data: dict) -> Any:
        """
        Decode a dictionary representation back to a value.

        Parameters
        ----------
        encoded_data : dict
            The dictionary containing encoded data to decode.

        Returns
        -------
        Any
            The decoded value, typically an instance of the `_class`.
        """
        pass
