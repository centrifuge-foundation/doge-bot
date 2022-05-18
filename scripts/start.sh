#!/usr/bin/env bash

if [[ -z "$DOGE_USER_ID" ]]; then
    echo "You must specify DOGE_USER_ID"
    exit 1
fi

if [[ -z "$DOGE_ACCESS_TOKEN" ]]; then
    echo "You must specify DOGE_ACCESS_TOKEN"
    exit 1
fi

homeserver=`echo ${DOGE_HOMESERVER:-https://matrix-client.matrix.org} | jq -R`
user_id=`echo $DOGE_USER_ID | jq -R`
access_token=`echo $DOGE_ACCESS_TOKEN | jq -R`
device_id=`echo ${DOGE_DEVICE_ID:-null} | jq -R`

project=`dirname $(dirname $0)`
temp_config=`mktemp`

python -m maubot.standalone -c <(
    cat `realpath "$project/example-config.yaml"` \
        | yq ".user.credentials.id |= $user_id" \
        | yq ".user.credentials.homeserver |= $homeserver" \
        | yq ".user.credentials.access_token |= $access_token" \
        | yq ".user.credentials.device_id |= $device_id"
) -m "$project/maubot.yaml" "$@"
