#!/usr/bin/env bash

read -ep "Homeserver: " -i https://matrix-client.matrix.org homeserver
read -ep "Username: " -i "$1" username
read -erp "Password: " -s password
echo

curl -\#d@- "${homeserver}/_matrix/client/r0/login" <<EOF | jq .
{
  "type": "m.login.password",
  "identifier": {
    "type": "m.id.user",
    "user": $(echo $username | jq -R)
  },
  "password": $(echo $password | jq -R)
}
EOF
