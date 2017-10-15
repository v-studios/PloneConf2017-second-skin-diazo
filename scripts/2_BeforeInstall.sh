#!/bin/bash
# This runs before our code is moved into the appspec.yml's 'file' destination

# Update apt cache
apt-get update

# Install python (python2.7). (Ubuntu only ships with python3.)
# We also need git to retrieve our unpublished version of Tropo's AWACS.
apt-get install -y git python python-setuptools python-dev build-essential

# Install libxml and friends so buildout doesn't have to build it.
apt-get install -y libxml2-dev libxslt-dev zlib1g-dev libpcre3-dev libffi-dev libssl-dev

# Bootstrap python environment.
easy_install pip && pip install virtualenv
