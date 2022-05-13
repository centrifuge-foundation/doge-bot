# doge-bot

> Group management bot for [Matrix](matrix.io)

## Usage

Copy [`example-config.yaml`](./example-config.yaml) and configure bot credentials.

Start the bot in standalone mode by running `doge -c [config file]`.

### List of commands:

- `!groups` - list all existing groups
- `!create [group name]` - create a new group
- `!delete [group name]` - delete an existing group
- `!add [group name] [user id]` - add a new member to the group
- `!remove [group name] [user id]` - remove an exsiting member from the group
- `!join [group name] [room alias or id]` - invite group members to the room
- `!leave [group name] [room alias or id]` - remove group members from the room

## Development





### Generating access token

> This section describes a way to generate access token using Maubot API, but there may be other ways to generate a Matrix access tokens

Copy [example server configuration file](https://raw.githubusercontent.com/maubot/maubot/master/maubot/example-config.yaml), changing admin username and password, and adding your homeserver if necessary. 

Start Maubot server, specifying path to the configuration file:

```
python -m maubot -c <config path>
```

Authenticate with the server using admin credentials from the configuration file:

```
mbc login -u <admin username>
```

Generate access token, specifying a homeserver and a fully-qualified user id:
```
mbc auth -h <homeserver> -u <user id>
```


## Development

Enter the development environment by running `nix-shell` (or `nix develop` when using [Flakes](https://nixos.wiki/wiki/Flakes))
