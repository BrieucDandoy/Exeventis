from __future__ import annotations

from abc import ABC
from collections.abc import MutableMapping
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Union
from uuid import UUID

from pydantic import BaseModel


class TranscoderStore(MutableMapping):
    def __init__(self):
        self._transcoders: Dict[Union[str, type], Transcoder] = {}

    def add(self, transcoder: Transcoder):
        self._transcoders[transcoder.name] = transcoder
        self._transcoders[transcoder._class] = transcoder

    def remove(self, key: Union[str, type]):
        transcoder = self._transcoders.pop(key, None)
        if transcoder:
            if isinstance(key, str):
                self._transcoders.pop(transcoder.__class__, None)
            else:
                self._transcoders.pop(transcoder.name, None)

    def get(self, key, default) -> Transcoder | Any:
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
        cls = obj.__class__
        if cls in self:
            transcoder = self[cls]
            return {"_key_": transcoder.name, "_value_": transcoder.encode(obj)}
        raise TypeError(f"Object of type {cls.__name__} is not JSON serializable")

    def object_hook(self, obj: dict) -> Any:
        if "_key_" in obj and "_value_" in obj:
            transcoder = self._transcoders[obj["_key_"]]
            return transcoder.decode(obj["_value_"])
        return obj


class Transcoder(ABC):
    name: str
    _class: type

    def __init__(self, name: str, _class: type):
        self.name = name
        self._class = _class

    def encode(self, data: Any) -> str:
        raise NotImplementedError

    def decode(self, encoded_data: dict) -> Any:
        raise NotImplementedError


class UUIDTranscoder(Transcoder):
    def __init__(self):
        self.name = "__UUID__"
        self._class = UUID

    def encode(self, data: UUID) -> str:
        return str(data)

    def decode(self, encoded_data) -> UUID:
        return UUID(encoded_data)


class DatetimeTranscoder(Transcoder):
    def __init__(self):
        self.name = "__datetime__"
        self._class = datetime

    def encode(self, data: datetime):
        return data.isoformat()

    def decode(self, encoded_data: str) -> datetime:
        return datetime.fromisoformat(encoded_data)


class PydanticTranscoder(Transcoder):
    name: str = str
    _class: BaseModel

    def encode(self, data: BaseModel) -> str:
        self.encode(data.model_dump())

    def decode(self, encoded_data: str) -> BaseModel:
        self._class.model_validate(encoded_data)


def create_transcoder_from_pydantic(
    name: str, model_class: type[BaseModel]
) -> type[PydanticTranscoder]:
    return type(
        name,  # Class name
        (PydanticTranscoder,),  # Base classes
        {"name": name, "_class": model_class},
    )
