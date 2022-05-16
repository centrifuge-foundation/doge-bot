# doge-bot

> Group management bot for [Matrix](matrix.io)

## Setup

[NixOS]() users can install the bot with the following command:

```
nix profile install github:kfactory-dev/doge-bot
```

## Usage

Copy [`example-config.yaml`](./example-config.yaml) to `config.yaml` and configure bot credentials.

Start the bot in standalone mode by running `doge-bot -c <config path>`.

### Available commands:

- `!groups` - list all existing groups
- `!create [group name]` - create a new group
- `!delete [group name]` - delete an existing group
- `!add [group name] [user id]` - add a new member to the group
- `!remove [group name] [user id]` - remove an exsiting member from the group
- `!join [group name] [room alias or id]` - invite group members to the room
- `!leave [group name] [room alias or id]` - remove group members from the room



## Development

This project uses [Nix Flakes]() to provide the development environment and build pipeline.

Run `nix develop` to enter the development environment, and `nix build` to build the bot.

You can also use `python -m maubot.standalone` to run the bot in the development environment.

### Generating access token

> The method described in this section uses Maubot server, but there are may be other ways to generate access token.

Copy [example server configuration file](https://raw.githubusercontent.com/maubot/maubot/master/maubot/example-config.yaml) changing admin username and password, and adding your homeserver if necessary.

Start Maubot server, specifying path to the server configuration file:

```

python -m maubot -c <server config path>

```

Authenticate with the server using admin credentials specified the configuration file:

```

mbc login -u <admin username>

```

Generate access token, specifying a homeserver and a fully-qualified user id:

```

mbc auth -h <homeserver> -u <user id>

```

```

```
