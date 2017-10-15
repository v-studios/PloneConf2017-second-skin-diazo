#!/bin/bash
# Run the test target; returns 0 on success, non-zero on failure
# which is what CodeDeploy needs.

cd /var/app

make prod_test

