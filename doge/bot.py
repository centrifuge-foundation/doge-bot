#!/usr/bin/env python3

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from io import StringIO
from typing import List, Optional, Union

from maubot import MessageEvent, Plugin
from maubot.handlers import command
from mautrix.errors.request import MNotFound
from mautrix.types import RoomAlias, RoomID, UserID
from sqlalchemy import event

from doge.db import DatabaseManager
from doge.entity import Base, Group, Room, User


class UserError(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        super().__init__(msg % args)


def synchronize(fn):
    @wraps(fn)
    def wrapper(self: Plugin, *args, **kwargs):
        self.loop.create_task(fn(self, *args, **kwargs))
    return wrapper


class DogeBot(Plugin):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tasks = []

    def listen(self, target, identifier, fn):
        "Listen for database events in the background"
        def listener(*args, **kwargs):
            task = self.loop.create_task(fn(*args, **kwargs))
            self.loop.run_until_complete(task)
            # self._tasks.append(task)
            # self._background.run_until_complete(task)
            print("Task created")

        event.listen(target, identifier, listener)

    async def start(self) -> None:
        await super().start()

        Base.metadata.create_all(self.database)

        self.listen(Group.users, "append", lambda group, user, *_:
                    self.invite_members(group, users=[user]))
        self.listen(Group.users, "remove", lambda group, user, *_:
                    self.remove_members(group, users=[user]))
        self.listen(Group.rooms, "append", lambda group, room, *_:
                    self.invite_members(group, rooms=[room]))
        self.listen(Group.rooms, "remove", lambda group, room, *_:
                    self.remove_members(group, rooms=[room]))

    @asynccontextmanager
    async def session(self, evt: Optional[MessageEvent] = None):
        dbm = DatabaseManager(self.database)
        try:
            yield dbm
            dbm.commit()
        except UserError as e:
            dbm.rollback()
            evt and await evt.respond("❌ %s" % e)
        except:
            dbm.rollback()
            evt and await evt.respond("❗ An error has occurred. Check logs for details.")
            raise
        finally:
            dbm.close()

    @command.new(name="groups", help="List existing groups")
    async def list_groups(self, evt: MessageEvent):
        with StringIO() as output:
            async with self.session(evt) as dbm:
                if not (groups := dbm.find_all_groups()):
                    print("*no groups*", file=output)
                for group in groups:
                    print("- **%s**" % (group.name), file=output)
                    if not group.rooms:
                        print("  - *no rooms*", file=output)
                    else:
                        print("  - rooms", file=output)
                    for room in group.rooms:
                        print("    - %s" % (room.room_alias), file=output)
                    if not group.users:
                        print("  - *no users*", file=output)
                    else:
                        print("  - users", file=output)
                    for user in group.users:
                        print("    - %s" % (user.user_id), file=output)
            await evt.respond(output.getvalue())

    @command.new(name="create", help="Create a new group")
    @command.argument("group_name", label="Group name")
    async def create_group(self, evt: MessageEvent, group_name: str) -> None:
        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is not None:
                raise UserError("Group **%s** already exist", group.name)

            dbm.add(group := Group(name=group_name))
            await evt.respond("✅ Group **%s** created" % (group.name))

    @command.new(name="delete", help="Create a new group")
    @command.argument("group_name", label="Group name")
    async def delete_group(self, evt: MessageEvent, group_name: str) -> None:
        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            dbm.delete(group)
            await self.remove_members(group)
            await evt.respond("✅ Group **%s** deleted" % (group.name))

    @command.new(name="add", help="Add user to group")
    @command.argument("group_name", label="Group name")
    @command.argument("user_name", label="User name")
    async def add_user_to_group(self, evt: MessageEvent, group_name: str, user_name: str) -> None:
        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            if (user := User(user_id=self.parse_user_id(user_name))) in group.users:
                raise UserError("User %s is already in group **%s**",
                                user.user_id, group.name)

            group.users.append(user)
            await evt.respond("✅ Added user %s to group **%s**" % (user.user_id, group.name))

    @command.new(name="remove", help="Remove user from group")
    @command.argument("group_name", label="Group name")
    @command.argument("user_name", label="User name")
    async def remove_user_from_group(self, evt: MessageEvent, group_name: str, user_name: str) -> None:
        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            if (user := User(user_id=self.parse_user_id(user_name))) not in group.users:
                raise UserError("User %s is not in group **%s**",
                                user.user_id, group.name)

            group.users.remove(user)
            await evt.respond("✅ Removed user %s from group **%s**" % (user.user_id, group.name))

    @command.new(name="join", help="Add group to room")
    @command.argument("group_name", label="Group name")
    @command.argument("room_id_or_alias", label="Room id or alias")
    async def add_group_to_room(self, evt: MessageEvent, group_name: str, room_id_or_alias: str) -> None:
        room_id_or_alias = self.parse_room_id_or_alias(room_id_or_alias)

        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            if (room := await self.resolve_room(room_id_or_alias)) in group.rooms:
                raise UserError("Group **%s** is already in room %s",
                                group.name, room.room_alias)

            if room.room_id not in await self.client.get_joined_rooms():
                await self.client.join_room_by_id(room.room_id)

            group.rooms.append(room)
            await evt.respond("✅ Added group **%s** to room %s" % (group.name, room.room_alias))

    @command.new(name="leave", help="Remove group from room")
    @command.argument("group_name", label="Group name")
    @command.argument("room_id_or_alias", label="Room id or alias")
    async def remove_group_from_room(self, evt: MessageEvent, group_name: str, room_id_or_alias: str) -> None:
        room_id_or_alias = self.parse_room_id_or_alias(room_id_or_alias)

        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            if (room := await self.resolve_room(room_id_or_alias)) not in group.rooms:
                raise UserError("Group **%s** is not in room %s",
                                group.name, room.room_alias)

            group.rooms.remove(room)
            await evt.respond("✅ Removed group **%s** from room %s" % (group.name, room.room_alias))

    async def invite_members(self, group: Group, rooms: Optional[List[Room]] = None, users: Optional[List[User]] = None):
        for room in rooms or group.rooms:
            self.log.debug("Inviting %s users to %s", group, room)

            members = await self.client.get_joined_members()
            self.log.debug("%s members: %s", room, ", ".join(members.keys()))

            for user in users or group.users:
                if user in members:
                    self.log.debug("Not inviting %s to %s", user, room)
                    continue

                self.log.debug("Inviting %s to %s", user, room)
                await self.client.invite_user(room.room_id, user.user_id)

    async def remove_members(self, group: Group, rooms: Optional[List[Room]] = None, users: Optional[List[User]] = None):
        with self.session() as db:
            for room in rooms or group.rooms:
                self.log.debug("Inviting %s users to %s", group, room)

                other_groups = [other_group for other_group in db.find_groups_by_room(
                    room) if other_group != group]
                self.log.debug("%s groups: %s", room, ", ".join(other_groups))

                for user in users or group.users:
                    if user in other_group_users:
                        self.log.debug("Not removing %s from %s", user, room)
                        continue

                    self.log.debug("Removing user %s from %s", user, room)
                    await self.client.kick_user(room.room_id, user.user_id)

    def parse_user_id(self, user_id: str) -> UserID:
        if not user_id.startswith("@"):
            user_id = "@" + user_id
        if not ":" in user_id:
            user_id = user_id + ":" + self.client.domain
        return UserID(user_id)

    def parse_room_id_or_alias(self, room_id_or_alias: str) -> Union[RoomID, RoomAlias]:
        if ":" not in room_id_or_alias:
            room_id_or_alias = room_id_or_alias + ":" + self.client.domain

        if room_id_or_alias.startswith("!"):
            return RoomID(room_id_or_alias)

        if not room_id_or_alias.startswith("#"):
            room_id_or_alias = "#" + room_id_or_alias

        return RoomAlias(room_id_or_alias)

    async def resolve_room(self, room_id_or_alias: Union[RoomID, RoomAlias]) -> Room:
        if (room_alias := room_id_or_alias).startswith("!"):
            return Room(room_id=room_id_or_alias)

        try:
            info = await self.client.resolve_room_alias(room_alias)
            return Room(room_id=info.room_id, room_alias=room_alias)
        except MNotFound:
            raise UserError("Room alias %s not found", room_id_or_alias)
