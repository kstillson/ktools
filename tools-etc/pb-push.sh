#!/bin/bash

# Provides a simple interface for sending push notifications via the "Push
# Bullet" service.  Integrates with kmc to retrieve the needed access token.
# (You'll need to get your own access token to make use of this.)

# Reference doc:  https://docs.pushbullet.com/#create-push

# Ken-specific note: "Tasker" app on Android phone uses contents to change
# audible alert done.  Prefix MSG with "#a," to escalate to alert tone, or
# "#i," to de-escalate to information-only notification tone.

# Required params
MSG="$@1"
if [[ "$MSG" == "" ]]; then echo "Error- must provide message to send as params." >&2 ; exit 3; fi

# Optional environment variable controls.
DEFAULT_RATE_LIMIT=${DEFAULT_RATE_LIMIT:-2,240}  # Allow 2 pushes every 4 minutes.
LOG=${PB_LOG:-/var/log/homesec/pb-push.log}
RL_FILE=${RL_FILE:-/tmp/pb.rl}
ACCESS_TOKEN=${PB_TOKEN}

if [[ ! -f "${RL_FILE}" ]]; then ratelimiter -i $DEFAULT_RATE_LIMIT $RL_FILE; fi
ratelimiter ${RL_FILE} || { { echo "$(date): RATELIMITED: $MSG" | tee -a $LOG; } >&2 ; exit 1; }

if [[ "$ACCESS_TOKEN" == "" ]]; then
    ACCESS_TOKEN=$(/usr/local/bin/kmc pb-push)
fi
if [[ "$ACCESS_TOKEN" == "" || "$ACCESS_TOKEN" == *Error* ]]; then
    echo "unable to get access token" | tee -a $LOG >&2
    exit 2
fi

echo "$(date): $MSG" >> $LOG
curl -sS -m 5 --header "Access-Token: ${ACCESS_TOKEN}" \
     --header 'Content-Type: application/json' \
     --data "{\"body\":\"${MSG}\",\"type\":\"note\"}" \
     --request POST -sS \
     https://api.pushbullet.com/v2/pushes  |& tee -a $LOG

exit $?
