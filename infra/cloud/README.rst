=============================
 README Cloud Infrastructure
=============================

This tree holds code that builds cloud infrastructure, whether with
troposphere or boto-scripts for things that tropo can't do.

Cloud configs are driven by .ini files at the top level of the repo,
based on target environment:

* local.ini: your laptop (see original proxy.ini)
* stage.ini: for temporary customer-approval instances sans ELB/ASG
* prod.ini: production AWS with ELB and ASG (min=max=2)

The AWS infrastructure we need will be:

* ALL:

  * S3: code: for ALL environments
  * IGW
  * Route53
  * VPC
  * NAT?
  * SG: HTTP/HTTPS for public, ssh for Devs

* Local (dev)

  * no AWS cloud infrastructure

* Stage (customer preview, not 24x7)

  * EC2

* Prod (24x7)

  * ELB
  * ASG: min=2, max=2 high-availability but no scaling up
  * EC2


Install
=======

Create virtualenv::

  virtualenv --python3 .venv3
  source .venv3/bin/activate
  pip install -r requirements.txt

Run
===

Set your AWS creds for the appropriate environment, then run::

  ./infra.py $env.ini

