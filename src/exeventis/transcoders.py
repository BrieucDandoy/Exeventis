from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Union
from uuid import UUID

from pydantic import BaseModel

from exeventis.abc import Transcoder


class TranscoderStore(MutableMapping):
    """
    A registry for managing `Transcoder` instances used for (de)serialization.

    Transcoders can be registered by name or by the class they encode. This store provides
    default methods for integrating with `json.dumps()` and `json.loads()` via the `default`
    and `object_hook` callbacks.

    This is particularly useful for storing and restoring rich Python objects (e.g., `UUID`,
    `datetime`, `pydantic.BaseModel`) inside JSON structures.

    Examples
    --------
    >>> store = TranscoderStore()
    >>> store.add(UUIDTranscoder())
    >>> encoded = json.dumps({"id": uuid.uuid4()}, default=store.default)
    >>> decoded = json.loads(encoded, object_hook=store.object_hook)

    Attributes
    ----------
    _transcoders : dict[Union[str, type], Transcoder]
        Internal mapping from names and types to registered transcoders.

    Methods
    -------
    add(transcoder: Transcoder)
        Registers a transcoder by both its name and class.
    remove(key: Union[str, type])
        Unregisters a transcoder by its name or class.
    get(key, default)
        Gets a transcoder if registered, otherwise returns the provided default.
    default(obj)
        JSON serialization hook. Encodes known objects using their associated transcoder.
    object_hook(obj: dict)
        JSON deserialization hook. Decodes objects previously encoded via `default`.
    """

    def __init__(self):
        """
        Initializes an empty transcoder store.
        """
        self._transcoders: Dict[Union[str, type], Transcoder] = {}

    def add(self, transcoder: Transcoder):
        """
        Registers a transcoder under both its name and type.

        Parameters
        ----------
        transcoder : Transcoder
            The transcoder to register.
        """
        self._transcoders[transcoder.name] = transcoder
        self._transcoders[transcoder._class] = transcoder

    def remove(self, key: Union[str, type]):
        """
        Unregisters a transcoder by either its name or class.

        Parameters
        ----------
        key : str or type
            The identifier used during registration.
        """
        transcoder = self._transcoders.pop(key, None)
        if transcoder:
            if isinstance(key, str):
                self._transcoders.pop(transcoder.__class__, None)
            else:
                self._transcoders.pop(transcoder.name, None)

    def get(self, key, default) -> Transcoder | Any:
        """
        Returns the transcoder associated with the key, or a default value.

        Parameters
        ----------
        key : str or type
            Identifier to lookup.
        default : Any
            Value to return if key is not found.

        Returns
        -------
        Transcoder or Any
            The corresponding transcoder or the default.
        """
        if key in self:
            return self[key]
        return default

    def __getitem__(self, key: Union[str, type]) -> Transcoder:
        return self._transcoders[key]

    def __setitem__(self, key: Union[str, type], value: Transcoder) -> None:
        self._transcoders[key] = value

    def __delitem__(self, key: Union[str, type]) -> None:
        self.remove(key)

    def __iter__(self) -> Iterator[Union[str, type]]:
        return iter(self._transcoders)

    def __len__(self) -> int:
        return len(self._transcoders)

    def default(self, obj):
        """
        Hook for JSON encoding (to be passed to `json.dumps`).

        Parameters
        ----------
        obj : Any
            The object to encode.

        Returns
        -------
        dict
            A serializable representation of the object.

        Raises
        ------
        TypeError
            If the object's class is not registered.
        """
        cls = obj.__class__
        if cls in self:
            transcoder = self[cls]
            return {"_key_": transcoder.name, "_value_": transcoder.encode(obj)}
        raise TypeError(f"Object of type {cls.__name__} is not JSON serializable")

    def object_hook(self, obj: dict) -> Any:
        """
        Hook for JSON decoding (to be passed to `json.loads`).

        Parameters
        ----------
        obj : dict
            A dictionary parsed from JSON.

        Returns
        -------
        Any
            The decoded object if recognized, otherwise the original dict.
        """
        print(f"object_hook for {obj}")
        if "_key_" in obj and "_value_" in obj:
            transcoder = self._transcoders[obj["_key_"]]
            return transcoder.decode(obj["_value_"])
        return obj


class UUIDTranscoder(Transcoder):
    """
    Transcoder for UUID objects.

    Converts UUID instances to their string representation and vice versa.

    Attributes
    ----------
    name : str
        The unique identifier for this transcoder ("__UUID__").
    _class : type
        The class handled by this transcoder (`UUID`).
    """

    def __init__(self):
        """
        Initialize the UUIDTranscoder with predefined name and class.
        """
        self.name = "__UUID__"
        self._class = UUID

    def encode(self, data: UUID) -> str:
        """
        Encode a UUID to a string.

        Parameters
        ----------
        data : UUID
            UUID to encode.

        Returns
        -------
        str
            String representation of the UUID.
        """
        return str(data)

    def decode(self, encoded_data) -> UUID:
        """
        Decode a string into a UUID.

        Parameters
        ----------
        encoded_data : str
            String to decode.

        Returns
        -------
        UUID
            Decoded UUID object.
        """
        return UUID(encoded_data)


class DatetimeTranscoder(Transcoder):
    """
    Transcoder for datetime objects.

    Converts datetime instances to ISO 8601 strings and back.

    Attributes
    ----------
    name : str
        The unique identifier for this transcoder ("__datetime__").
    _class : type
        The class handled by this transcoder (`datetime`).
    """

    def __init__(self):
        """
        Initialize the DatetimeTranscoder with predefined name and class.
        """
        self.name = "__datetime__"
        self._class = datetime

    def encode(self, data: datetime):
        """
        Encode a datetime object to an ISO 8601 string.

        Parameters
        ----------
        data : datetime
            Datetime object to encode.

        Returns
        -------
        str
            ISO 8601 formatted string.
        """
        return data.isoformat()

    def decode(self, encoded_data: str) -> datetime:
        """
        Decode an ISO 8601 string to a datetime object.

        Parameters
        ----------
        encoded_data : str
            ISO 8601 formatted string.

        Returns
        -------
        datetime
            Decoded datetime object.
        """
        return datetime.fromisoformat(encoded_data)


class PydanticTranscoder(Transcoder):
    """
    Transcoder for Pydantic BaseModel instances.

    Serializes a Pydantic model to a JSON string and deserializes it back to a model instance.

    Attributes
    ----------
    name : str
        Identifier for the transcoder.
    _class : BaseModel
        The specific Pydantic model class this transcoder handles.

    Methods
    -------
    encode(data: BaseModel) -> str
        Serialize a Pydantic model instance to a JSON string.
    decode(encoded_data: str) -> BaseModel
        Deserialize a dict into a Pydantic model instance.
    """

    name: str = str
    _class: BaseModel

    def encode(self, data: BaseModel) -> str:
        """
        Encode a Pydantic model to a JSON string.

        Parameters
        ----------
        data : BaseModel
            The model instance to encode.

        Returns
        -------
        str
            JSON string representation of the model.
        """
        self.encode(data.model_dump_json())

    def decode(self, encoded_data: str) -> BaseModel:
        """
        Decode a dict into a Pydantic model instance.

        Parameters
        ----------
        encoded_data : str
            JSON string representation of the model.

        Returns
        -------
        BaseModel
            An instance of the `_class` Pydantic model.
        """
        self._class.model_validate(encoded_data)


def BaseModel_transcoder_factory(
    name: str, model_class: type[BaseModel]
) -> type[PydanticTranscoder]:
    """
    Factory function to dynamically create a PydanticTranscoder subclass for a specific model.

    Parameters
    ----------
    name : str
        The name of the generated transcoder class.
    model_class : type[BaseModel]
        The Pydantic model class the transcoder will handle.

    Returns
    -------
    type[PydanticTranscoder]
        A dynamically generated subclass of `PydanticTranscoder` configured for the given model.

    Examples
    --------
    >>> User = pydantic.BaseModel.construct(...)  # Your Pydantic model
    >>> UserTranscoder = BaseModel_transcoder_factory("UserTranscoder", User)
    >>> transcoder = UserTranscoder()
    """
    return type(
        name,
        (PydanticTranscoder,),
        {"name": name, "_class": model_class},
    )


class StandartTranscoderStore(TranscoderStore):
    def __init__(self):
        super().__init__()
        self.add(DatetimeTranscoder())
        self.add(UUIDTranscoder())
