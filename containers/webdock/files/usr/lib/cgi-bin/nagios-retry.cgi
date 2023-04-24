#!/bin/bash
/usr/local/bin/nag --retry --html --status_file /var/nagios/status.dat --cmd_file /var/nagios/rw/nagios.cmd
