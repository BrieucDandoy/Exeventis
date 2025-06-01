from __future__ import annotations

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from exeventis.abc import Reconstructor
from exeventis.abc import Recorder
from exeventis.aggregate import Aggregate
from exeventis.aggregate import Event
from exeventis.reconstructor import StandartReconstructor
from exeventis.transcoders import TranscoderStore

Base = declarative_base()


class SqlRecorder(Recorder):
    """
    Recorder that persists events to a SQL database using SQLAlchemy.

    This class allows events to be stored and retrieved from a relational database.
    It uses SQLAlchemy to handle ORM mapping and session management.
    It supports event filtering based on version and timestamp and reconstructs aggregates
    using a priority strategy.

    Parameters
    ----------
    database_url : str
        Database connection URL (e.g., 'sqlite:///mydb.db').
    transcoder_store : TranscoderStore
        Store to encode/decode complex Python objects in event payloads.
    aggregates_types : list[type[Aggregate]], optional
        List of aggregate types this recorder is responsible for. Defaults to `[Aggregate]`.
    name : str, optional
        Optional name identifier for the recorder.
    reconstructor : Reconstructor, optional
        Custom reconstructor to rebuild aggregates from event streams. If not provided,
        a default `Reconstructor` is used.

    Methods
    -------
    add(event: Event)
        Saves an event to the database.
    get(originator_id: UUID, max_timestamp: datetime, max_version: int, priority: Priority) -> Aggregate
        Retrieves and reconstructs an aggregate from stored events.
    """

    def __init__(
        self,
        database_url: str,
        transcoder_store: TranscoderStore,
        aggregates_types=[Aggregate],
        name: Optional[str] = None,
        reconstructor: Optional[Reconstructor] = None,
    ):
        super().__init__(aggregates_types, name)
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
        self.transcoder_store = transcoder_store
        if not reconstructor:
            self.reconstructor = StandartReconstructor()
        else:
            self.reconstructor = reconstructor

    def add(self, event: Event):
        orm_event = EventORM.from_event(event, transcoder_store=self.transcoder_store)
        with self.session_maker() as session:
            session.add(orm_event)
            session.commit()

    def get(
        self,
        originator_id: UUID,
        max_timestamp: Optional[datetime] = None,
        max_version: Optional[int] = None,
    ) -> Aggregate:
        with self.session_maker() as session:
            query = session.query(EventORM).filter(EventORM.originator_id == originator_id)

            if max_version is not None:
                query = query.filter(EventORM.version <= max_version)

            if max_timestamp is not None:
                query = query.filter(EventORM.timestamp <= max_timestamp)

            events_orm = query.all()
            print(events_orm)
            events = [event.to_event(self.transcoder_store) for event in events_orm]
            aggregate = self.reconstructor.reconstruct(events)
        return aggregate

    def save(self, event_list: list[Event]):
        with self.session_maker() as session:
            session.add_all(
                [
                    EventORM.from_event(event, transcoder_store=self.transcoder_store)
                    for event in event_list
                ]
            )
            session.commit()


class EventORM(Base):
    """
    SQLAlchemy ORM model for persisting Event instances to a relational database.

    This class defines the schema of the "events" table and provides utilities
    to convert between `Event` domain objects and their database representation.

    Table
    -----
    __tablename__ : str
        Name of the SQL table. Set to "events".

    Columns
    -------
    id : int
        Primary key, autoincremented.
    name : str
        Name of the event (e.g., 'created', 'updated').
    type_ : str
        Dotted path to the aggregate type (used for reconstruction).
    event_kwargs : str
        Serialized JSON string of keyword arguments used when applying the event.
    version : int
        Version number of the aggregate at the time the event was created.
    timestamp : datetime
        Time the event occurred.
    originator_id : UUID
        UUID of the aggregate that generated the event.

    Methods
    -------
    from_event(event: Event, transcoder_store: TranscoderStore) -> EventORM
        Converts a domain `Event` to a database-compatible `EventORM`.
    to_event(transcoder_store: TranscoderStore) -> Event
        Converts this ORM object back to a domain-level `Event`.
    __repr__() -> str
        Returns a human-readable representation of the EventORM instance.
    """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    type_ = Column(String, nullable=False)
    event_kwargs = Column(String, nullable=True)
    version = Column(Integer, nullable=False)
    timestamp = Column(DateTime)
    originator_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    def __repr__(self):
        return (
            f"<EventORM(name={self.name}, type_={self.type_}, originator_id={self.originator_id}, "
            f"version={self.version}, timestamp={self.timestamp},event_kwargs={self.event_kwargs})>"
        )

    @classmethod
    def from_event(
        cls: type[EventORM], event: Event, transcoder_store: TranscoderStore
    ) -> EventORM:
        return cls(
            name=event.name,
            type_=event.type_,
            event_kwargs=json.dumps(event.event_kwargs, default=transcoder_store.default),
            originator_id=event.originator_id,
            version=event.version,
            timestamp=event.timestamp,
        )

    def to_event(self, transcoder_store: TranscoderStore) -> Event:
        return Event(
            name=self.name,
            type_=self.type_,
            event_kwargs=json.loads(self.event_kwargs, object_hook=transcoder_store.object_hook),
            originator_id=self.originator_id,
            version=self.version,
            timestamp=self.timestamp,
        )
