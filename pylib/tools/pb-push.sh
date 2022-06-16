#!/bin/bash

# TODO: rewrite in python3

# Send message provided on command-line to push-bullet, with rate-limiting.
# Note: 
# https://docs.pushbullet.com/#create-push

# Ken-specific: "Tasker" app on Android phone uses contents to change
# audible alert done.  Include "#a" to escalate to alert tone, or
# #i to de-escalate to information-only notification tone.

MSG="$@"

DEFAULT_RATE_LIMIT=${DEFAULT_RATE_LIMIT:-2,240}  # Allow 2 pushes every 4 minutes.
LOG=${PB_LOG:-/var/log/apache2/pb-push.log}
RL_FILE=${RL_FILE:-/tmp/pb.rl}

# TODO: somewhat Ken specific.
# Default LOG location is in the apache log dir.  But if that doesn't
# exist, it indicates this script is being called from outside docker,
# so instead use the full host path to the same file.
if [[ ! -f "${LOG}" ]]; then
  LOG="/rw/dv/webdock/var_log_apache2/pb-push.log"
fi

if [[ ! -f "${RL_FILE}" ]]; then ratelimiter -i $DEFAULT_RATE_LIMIT $RL_FILE; fi
ratelimiter ${RL_FILE} || { { echo "$(date): RATELIMITED: $MSG" | tee -a $LOG; } >&2 ; exit 1; }

ACCESS_TOKEN=$(/usr/local/bin/kmc pb-push)
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
