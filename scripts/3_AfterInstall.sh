#!/bin/bash
chmod -R 755 /var/app

# Enter App install dir which CodeDeploy created from our distro, per
# the appspec.yml's "files" directive
cd /var/app

# Bootstrap the virtualenv, build diazo and nginx.
make clean prod_build

