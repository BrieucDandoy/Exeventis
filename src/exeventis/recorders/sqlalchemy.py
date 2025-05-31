from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from exeventis.aggregate import Event
from exeventis.recorders.base import EventRecorder
from exeventis.transcoders import TranscoderStore

Base = declarative_base()


class PsqlRecorder(EventRecorder):
    def __init__(
        self,
        database_url: str,
        transcoder_store: TranscoderStore,
        aggregates_types=...,
        name: Optional[str] = None,
    ):
        super().__init__(aggregates_types, name)
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
        self.transcoder_store = transcoder_store

    def add(self, event: Event):
        orm_event = EventORM.from_event(event)
        with self.session_maker() as session:
            session.add(orm_event)
            session.commit()

    def get(self, originator_id: UUID):
        with self.session_maker() as session:
            events_orm = (
                session.query(EventORM)
                .filter(EventORM.originator_id == originator_id)
                .all()
            )
            return [event.to_event(self.transcoder_store) for event in events_orm]


class EventORM(Base):
    __tablename__ = "events"

    id = Column(Integer(as_uuid=True), primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    type_ = Column(String, nullable=False)
    event_kwargs = Column(String, nullable=True)
    version = Column(Integer, nullable=False)
    timestamp = Column(DateTime)
    originator_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    def __repr__(self):
        return (
            f"<EventORM(name={self.name}, type_={self.type_}, "
            f"originator_id={self.originator_id})>"
        )

    @classmethod
    def from_event(
        cls: type[EventORM], event: Event, transcoder_store: TranscoderStore
    ) -> EventORM:
        return cls(
            name=event.name,
            type_=event.type_,
            event_kwargs=json.load(
                event.event_kwargs, object_hook=transcoder_store.object_hook
            ),
            originator_id=event.originator_id,
        )

    def to_event(self, transcoder_store: TranscoderStore) -> Event:
        return Event(
            name=self.name,
            type_=self.type_,
            event_kwargs=json.dumps(
                self.event_kwargs, default=transcoder_store.default
            ),
            originator_id=self.originator_id,
        )
