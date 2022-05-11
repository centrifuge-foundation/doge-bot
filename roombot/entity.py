from enum import unique
from typing import Iterable, List
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Group(Base):
    __tablename__ = 'group'
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String, unique=True, nullable=False)
    users = relationship("User", cascade="all, delete-orphan")
    rooms = relationship("Room", cascade="all, delete-orphan")

    def __eq__(self, obj: object) -> bool:
        return isinstance(obj, Group) and obj.name == self.name

    def __str__(self) -> str:
        return "Group(id=%r, name=%r)" % (self.id, self.name)


class User(Base):
    __tablename__ = 'user'
    group_id = Column(Integer, ForeignKey("group.id"), primary_key=True)
    user_id = Column(String, primary_key=True)

    def __eq__(self, obj: object) -> bool:
        return isinstance(obj, User) and obj.user_id == self.user_id


class Room(Base):
    __tablename__ = 'group_room'
    group_id = Column(Integer, ForeignKey("group.id"), primary_key=True)
    room_id = Column(String, primary_key=True)
    room_alias = Column(String)

    def __eq__(self, obj: object) -> bool:
        return isinstance(obj, Room) and obj.room_id == self.room_id

    @property
    def room_alias_or_id(self):
        return self.room_alias or self.room_id
