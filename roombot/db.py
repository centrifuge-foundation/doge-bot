from typing import Iterable, Optional

from sqlalchemy.orm import Session, joinedload

from .entities import Group, Room, User


class DatabaseManager(Session):
    @property
    def groups_query(self):
        return self.query(Group).options(joinedload(Group.rooms)).options(joinedload(Group.users))

    def get_group_by_name(self, name: str) -> Optional[Group]:
        return self.groups_query.filter_by(name=name).one_or_none()

    def find_all_groups(self) -> Iterable[Group]:
        return self.groups_query.all()

    def find_groups_by_room(self, room: Room) -> Iterable[Group]:
        return (group for group in self.find_all_groups() if room in group.rooms)

    def find_groups_by_user(self, user: User) -> Iterable[Group]:
        return (group for group in self.find_all_groups() if user in group.users)
