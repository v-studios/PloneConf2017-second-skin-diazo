#!/bin/bash
# The OLD version of this file is executed before our code is
# installed to appspec.yml 'files' destination.
#
# Return 0 so CodeDeploy doesn't fail if the proc wasn't found.
# Would be better to test for /var/app/var/nginx.pid and kill that PID if the file exists.

echo "$0 (stop_server) is running from PWD=`pwd`"
pkill nginx  || echo "Could not pkill nginx"
exit 0
