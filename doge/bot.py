#!/usr/bin/env python3

from contextlib import asynccontextmanager
from functools import wraps
from io import StringIO
from typing import Optional, Union

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
    async def start(self) -> None:
        await super().start()

        Base.metadata.create_all(self.database)

        event.listen(Group.users, "append", self.invite_user_to_group_rooms)
        event.listen(Group.users, "remove", self.remove_user_from_group_rooms)
        event.listen(Group.rooms, "append", self.invite_group_users_to_room)
        event.listen(Group.rooms, "remove", self.remove_group_users_from_room)

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

    @command.new()
    async def ping(self, evt: MessageEvent) -> None:
        await evt.reply("pong")

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

    @synchronize
    async def invite_user_to_group_rooms(self, group: Group, user: User, *_):
        self.log.debug("Inviting user %s to group **%s** rooms",
                       user.user_id, group.name)

        if not group.rooms:
            self.log.debug("Group **%s** is not in any rooms")

        for room in group.rooms:
            if user.user_id in await self.client.get_joined_members(room.room_id):
                self.log.debug("Not inviting user %s to room %s",
                               user.user_id, room.room_alias_or_id)
                continue

            self.log.debug("Inviting user %s to room %s",
                           user.user_id, room.room_alias_or_id)
            await self.client.invite_user(room.room_id, user.user_id)

    @synchronize
    async def remove_user_from_group_rooms(self, group, user, *_):
        self.log.debug("Removing user %s from group **%s** rooms",
                       user.user_id, group.name)
        async with self.session() as dbm:
            if not group.rooms:
                self.log.debug("Group **%s** is not in any rooms")
            for room in group.rooms:
                if any(group != other_group and user in other_group.users
                       for other_group in dbm.find_groups_by_room(room)):
                    self.log.debug("Not removing user %s from room %s",
                                   user.user_id, room.room_alias_or_id)
                    continue

                self.log.debug("Removing user %s from room %s",
                               user.user_id, room.room_alias_or_id)
                await self.client.kick_user(room.room_id, user.user_id)

    @synchronize
    async def invite_group_users_to_room(self, group, room, *_):
        self.log.debug("Inviting group **%s** users to room %s",
                       group.name, room.room_id)
        if not group.users:
            self.log.debug("Group **%s** does not have any users")
        for user in group.users:
            if user.user_id in await self.client.get_joined_members(room.room_id):
                self.log.debug("Not inviting user %s to room %s",
                               user.user_id, room.room_alias_or_id)
                continue

            self.log.debug("Inviting user %s to room %s",
                           user.user_id, room.room_alias_or_id)
            await self.client.invite_user(room.room_id, user.user_id)

    @synchronize
    async def remove_group_users_from_room(self, group, room, *_):
        self.log.debug("Removing group **%s** users from room %s",
                       group.name, room.room_id)
        async with self.session() as dbm:
            if not group.users:
                self.log.debug("Group **%s** does not have any users")
            for user in group.users:
                if any(group != other_group and user in other_group.users
                       for other_group in dbm.find_groups_by_room(room)):
                    self.log.debug("Not removing user %s from room %s",
                                   user.user_id, room.room_alias_or_id)
                    continue

                self.log.debug("Removing user %s from room %s",
                               user.user_id, room.room_alias_or_id)
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
        if room_id_or_alias.startswith("!"):
            return Room(room_id=room_id_or_alias)
        else:
            room_alias = room_id_or_alias

        try:
            info = await self.client.resolve_room_alias(room_alias)
            return Room(room_id=info.room_id, room_alias=room_alias)
        except MNotFound:
            raise UserError("Room alias %s not found", room_id_or_alias)
