#!/bin/bash

# TODO: rewrite in python3

# Send message provided on command-line to push-bullet, with rate-limiting.
# Note: 
# https://docs.pushbullet.com/#create-push

# Ken-specific: "Tasker" app on Android phone uses contents to change
# audible alert done.  Include "#a" to escalate to alert tone, or
# #i to de-escalate to information-only notification tone.

MSG="$@"

DEFAULT_RATE_LIMIT="1,120"  # Allow 1 push every 2 minutes.
RL_FILE="/tmp/pb.rl"

# TODO: somewhat Ken specific.
# Default LOG location is in the apache log dir.  But if that doesn't
# exist, it indicates this script is being called from outside docker,
# so instead use the full host path to the same file.
LOG="/var/log/apache2/pb-push.log"
if [[ ! -f "${LOG}" ]]; then
  LOG="/rw/dv/webdock/var_log_apache2/pb-push.log"
fi

if [[ ! -f "${RL_FILE}" ]]; then ratelimiter -i $DEFAULT_RATE_LIMIT $RL_FILE; fi
ratelimiter /tmp/pb.rl || { echo "$(date): RATELIMITED: $MSG" >&2 |& tee -a $LOG; exit 1; }

ACCESS_TOKEN=$(/usr/local/bin/kmc pb-push)
if [[ "$ACCESS_TOKEN" == "" || "$ACCESS_TOKEN" == *Error* ]]; then
    echo "unable to get access token" >&2 |& tee -a $LOG
    exit 2
fi

echo "$(date): $MSG" >> $LOG
curl -sS -m 5 --header "Access-Token: ${ACCESS_TOKEN}" \
     --header 'Content-Type: application/json' \
     --data "{\"body\":\"${MSG}\",\"type\":\"note\"}" \
     --request POST -sS \
     https://api.pushbullet.com/v2/pushes  |& tee -a $LOG