# doge-bot

> Group management bot for [Matrix](matrix.io)

## Setup

[NixOS](https://nixos.org/) users can install the bot with the following command:

```
nix profile install github:kfactory-dev/doge-bot
```

Copy [`example-config.yaml`](./example-config.yaml) to `config.yaml` and configure bot credentials.

## Usage

Start the bot in standalone mode by running `doge-bot -c <config path>`.

**Available commands:**

- `!groups` - list all existing groups
- `!groups [group name] create` - create a new group
- `!groups [group name] rename [new name]` - rename a group
- `!groups [group name] delete` - delete a group
- `!groups [group name] add [user id]` - add member to the group
- `!groups [group name] remove [user id]` - remove member from the group
- `!groups [group name] join [room alias or id]` - invite group to the room
- `!groups [group name] leave [room alias or id]` - remove group from the room

[room alias or id]: 

### Docker image

[![Docker image](https://img.shields.io/docker/image/kfactory-dev/doge-bot.svg)](https://hub.docker.com/r/kfactory-dev/doge-bot)

You can also run the bot in a Docker container, by running the following command from the directory containing `config.yaml`:

```
docker run -v $PWD:/data:z -w /data kfactory-dev/doge-bot
```


## Development

This project uses [Nix Flakes](https://nixos.wiki/wiki/Flakes) to provide the development environment and build pipeline.

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
