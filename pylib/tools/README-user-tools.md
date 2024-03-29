
# Handy user-oriented tools

The tools subdirectory provides several command-line utilities that can also
be imported and used as Python libraries.


## kmc.py: key-master client

../services/keymaster provides a service for web-based secrets retrieval
(passwords, keys, etc).  "kmc" is a client interface for that service.  It
provides kcore/auth based authentication, retries, etc.


## nag.py: Nagios manipulation tool

This tool can read a Nagios state file and provide reports on current host and
service status in several different formats, or can take actions such as
requesting retries or acknowledging problems, by writing to the Nagios
incoming-command file.


### ratelimiter.py

Provides a tool that's easy to integrate with shell-scripts that can cause
actions to be limited to x-per-y-time.  You can have the action fail (i.e. be
skipped) if the rate-limit would be violated, or have the script hold a
command until the limit would be respected.

Note: needs to read+write a file to store desired limits and recent-usage
data.


### run_browser.py

Launch Chrome or Firefox with a bunch of security-oriented options.


### run_para.py

Runs command-line commands in parallel.  Keeps the stdout and stderr of each
job separated, and shows the real-time output of jobs in a dashboard.

See the module doc for various examples of what this is useful for.


### substring_counter.py

Replaces lines from stdin that match a list of substrings with a count of how
many lines were replaced.  I use this in tools-for-root/etc/rsnap-diff,
although I suspect it has many other uses.

