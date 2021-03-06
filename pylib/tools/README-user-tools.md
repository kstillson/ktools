
TODO(doc)

## ktools

The tools subdirectory provides several command-line utilities that can also
be imported as Python libraries.


### kmc.py: key-manager client

../services/keymanager provides a service for web-based secrets retrieval
(passwords, keys, etc).  "kmc" is the client interface for that service.  It
provides kcore/auth based authentication, retries, etc.


### pb-push.sh

Provides a simple interface for sending push notifications via the "Push
Bullet" service.  Integrates with kmc to retrieve access tokens.


### ratelimiter.py

Provides a tool that's easy to integrate with shell-scripts that can cause
actions to be limited to x-per-y-time.  You can have the action fail (i.e. be
skipped) if the rate-limit would be violated, or have the script hold a
command until the limit would be respected.

Note: needs an external file to store desired limits and recent-usage data.


### run_para.py

Runs (command-line) commands in parallel.  Keeps the stdout and stderr of each
job separated, and shows the real-time output of jobs in a dashboard.

See the module doc for various examples of what this is useful for.

