#!/usr/bin/env python3

from maubot import MessageEvent, Plugin
from maubot.handlers import command
from mautrix.types import RoomAlias, UserID
from mautrix.util.async_db import UpgradeTable

from .migrations import upgrade_table

class RoomBot(Plugin):
    @classmethod
    def get_db_upgrade_table(cls) -> UpgradeTable:
        return upgrade_table

    @command.new(help="Create a new group")
    @command.argument("group_name", label="Group name")
    async def create(self, evt: MessageEvent, group_name: str) -> None:
        room_alias = self.parse_room_alias(room_alias)
        try:
            room_id = await self.client.create_room(room_alias)
            await self.client.invite_user(room_id, evt.sender)
        except Exception as err:
            self.log.error(err)
            await evt.reply("{}".format(err))

    @command.new(help="Create a new room with bot and operator")
    @command.argument("room_alias", label="Room alias")
    async def create(self, evt: MessageEvent, room_alias: RoomAlias) -> None:
        room_alias = self.parse_room_alias(room_alias)
        try:
            room_id = await self.client.create_room(room_alias)
            await self.client.invite_user(room_id, evt.sender)
        except Exception as err:
            self.log.error(err)
            await evt.reply("{}".format(err))

    @command.new(help="Invite user into the current room")
    @command.argument("user_id", label="User ID")
    async def invite(self, evt: MessageEvent, user_id: UserID) -> None:
        user_id = self.parse_user_id(user_id)
        try:
            await self.client.invite_user(evt.room_id, user_id)
        except Exception as err:
            self.log.error(err)
            await evt.reply("{}".format(err))

    @command.new(help="Remove user from the current room")
    @command.argument("user_id", label="User ID", required=True)
    async def remove(self, evt: MessageEvent, user_id: UserID) -> None:
        user_id = self.parse_user_id(user_id)
        try:
            await self.client.kick_user(evt.room_id, user_id)
        except Exception as err:
            self.log.error(err)
            await evt.reply("{}".format(err))

    def parse_user_id(self, user_id: str) -> UserID:
        if not user_id.startswith("@"):
            user_id = "@" + user_id
        if not ":" in user_id:
            user_id = user_id + ":" + self.client.domain
        return UserID(user_id)

    def parse_room_alias(self, room_alias: str) -> UserID:
        if not room_alias.startswith("#"):
            room_alias = "#" + room_alias
        if not ":" in room_alias:
            room_alias = room_alias + ":" + self.client.domain
        return RoomAlias(room_alias)
