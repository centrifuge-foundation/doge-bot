#!/usr/bin/env python3

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from io import StringIO
from typing import List, Optional, Union

from maubot import MessageEvent, Plugin
from maubot.handlers import command
from mautrix.errors.request import MNotFound, MForbidden
from mautrix.types import RoomAlias, RoomID, UserID
from sqlalchemy import event

from doge.db import DatabaseManager
from doge.entity import Base, Group, Room, User


class UserError(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        super().__init__(msg % args)


class DogeBot(Plugin):
    async def start(self) -> None:
        await super().start()
        Base.metadata.create_all(self.database)

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
                        print("    - %s" % (room.room_alias_or_id), file=output)
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
            if dbm.get_group_by_name(group_name):
                raise UserError("Group **%s** already exists", group_name)

            dbm.add(Group(name=group_name))
            dbm.commit()

            await evt.respond("✅ Group **%s** created" % (group_name))

    @command.new(name="rename", help="Change group name")
    @command.argument("group_name", label="Group name")
    @command.argument("new_name", label="New name")
    async def rename_group(self, evt: MessageEvent, group_name: str, new_name: str) -> None:
        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            if dbm.get_group_by_name(new_name):
                raise UserError("Group **%s** already exists", new_name)

            group.name = new_name
            dbm.commit()

            await evt.respond("✅ Group **%s** renamed to **%s**" % (group_name, new_name))

    @command.new(name="delete", help="Delete a group")
    @command.argument("group_name", label="Group name")
    async def delete_group(self, evt: MessageEvent, group_name: str) -> None:
        async with self.session(evt) as dbm:
            if (group := dbm.get_group_by_name(group_name)) is None:
                raise UserError("Group **%s** does not exists", group_name)

            dbm.delete(group)
            dbm.commit()

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
            dbm.commit()

            await self.invite_members(group, users=[user])
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
            dbm.commit()

            await self.remove_members(group, users=[user])
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
                                group.name, room.room_alias_or_id)

            if room.room_id not in await self.client.get_joined_rooms():
                await self.client.join_room_by_id(room.room_id)

            group.rooms.append(room)
            dbm.commit()

            await self.invite_members(group, rooms=[room])
            await evt.respond("✅ Added group **%s** to room %s" % (group.name, room.room_alias_or_id))

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
                                group.name, room.room_alias_or_id)

            group.rooms.remove(room)
            dbm.commit()

            await self.remove_members(group, rooms=[room])
            await evt.respond("✅ Removed group **%s** from room %s" % (group.name, room.room_alias_or_id))

    async def invite_members(self, group: Group, rooms: Optional[List[Room]] = None, users: Optional[List[User]] = None):
        for room in rooms or group.rooms:
            self.log.debug("Inviting group %s users to room %s",
                           group.name, room.room_alias_or_id)

            members = await self.client.get_joined_members(room.room_id)
            self.log.debug("Room %s members: %s",
                           room.room_alias_or_id, ", ".join(members.keys()))

            for user in users or group.users:
                if user.user_id in members:
                    self.log.debug("User %s is already in room %s",
                                   user.user_id, room.room_alias_or_id)
                    continue

                self.log.debug("Inviting user %s to room %s",
                               user.user_id, room.room_alias_or_id)
                await self.client.invite_user(room.room_id, user.user_id)

    async def remove_members(self, group: Group, rooms: Optional[List[Room]] = None, users: Optional[List[User]] = None):
        async with self.session() as db:
            for room in rooms or group.rooms:
                self.log.debug("Removing group %s users from room %s",
                               group.name, room.room_alias_or_id)

                other_groups = [other_group for other_group in db.find_groups_by_room(
                    room) if other_group != group]
                self.log.debug("Room %s groups: %s", room.room_alias_or_id, ", ".join(
                    group.name for group in other_groups))

                for user in users or group.users:
                    if gs := [group for group in other_groups if user in group.users]:
                        self.log.debug("User %s is also in groups: %s",
                                       user.user_id, ", ".join(group.name for group in gs))
                        continue

                    self.log.debug("Removing user %s from %s",
                                   user.user_id, room.room_alias_or_id)
                    try:
                        await self.client.kick_user(room.room_id, user.user_id)
                    except MForbidden as e:
                        self.log.warn(e.message)

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
