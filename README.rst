===================================
 PloneConf2017 Diazo "Second Skin"
===================================

This code is a clone of the work we did for Trade To Travel, and
presented at Plone Conference 2017 -- it focussed on the tooling and
infrastructure rather than the theme itself. We've removed the actual
theme per the wishes of our client, as well as the AWS account
details, but everything else here remains the same.  This should get
you up and running with CloudFormation, Makefile-based buildouts,
running and testing front-end or full-stack, continuout integration
with CircleCI, and deployment to AWS with CodeDeploy.

You may find Troposphere/CloudFormation references to subnets and
databases that are not used for Diazo. We added another app, based
on Pyramid, to the same cloud infrastructure so the networking and
resources are defined here.

Intro
=====

Trade To Travel: Re-theme with Diazo to leave existing ASP site as the
backend, but with a modern front-end based on the Educo redesign.

Below we describe how to build and run it, how it's run on production,
and how to build it into Docker to test it.

Install and Run
===============

We've got two basic builds, one for Front-End developers which just
includes paster, and one for full-stack geeks that includes Nginx with
the XSLT module; the latter can be run on OS X and is deployed to
Ubuntu in production.

In each case -- front-end, fullstack, or docker -- we expose port 5000
so that the same tests can exercise the different builds.

You must have `virtualenv` installed, the Makefile will do the rest
for you.

The Makefile can remind you what you can build::

  make help

Front-End Developers: paster-only
---------------------------------

You probably should clean first, especially when switching branches::

  make clean

Then build, the default action::

  make

It will create a virtualenv, install the libraries, and do the buildout.

Then you can run the `paster` development server::

  make run

You don't even need to activate the virtualenv.

It will be accessible at:

  http://localhost:5000/

You can run the tests::

  make test

You can run browser tests as well. We don't commit passwords to code, so for
authenticated test to pass, set your environment vars::

  export TTT_MEMBER_USERNAME="..."
  export TTT_MEMBER_PASSWORD="..."
  export TTT_ADMIN_USERNAME="..."
  export TTT_ADMIN_PASSWORD="..."

To exercise the tests against Firefox::

  make test_browser

(Fullstack devs can run the browser tests too).

Full-Stack with Nginx and XSLT
------------------------------

Clean out the previous build::

  make clean

Build the full stack::

  make fullstack

That compile nginx with the patched XSLT module, compiles the Diazo
theme, and creates development and production nginx configurations.

You can run nginx locally, it binds to non-privileged ports::

  make fullstack_run

You can then connect to nginx theming server at:

  http://localhost:8888/

or the cache that sits in front at, the same port as the Front-End
developer instance uses, so that we can use the same tests:

  http://localhost:5000/

Run the tests with::

  make fullstack_test

You can stop the nginx daemon with::

  make fullstack_stop


Bind nginx cache to port 80 on Production
-----------------------------------------

To build for production you do similar to the above::

  make clean
  make prod_build

Then run it with the configuration that binds the cache to privileged
port 80, where users (actually, the AWS ELB) connect::

  make prod_run

You can connect to port 80, or bypass the cache and talk to Diazo on
the same 8888 port.  You can also run int in the foreground::

  make prod_run_fg

(There is no `prod_test` yet. See the card about implementing
CodeDeploy validation if you add prod tests).


How Nginx runs with the XSLT module: theme, conf, logs
------------------------------------------------------

We compile the rules and theme into an XSL file at::

  $THISDIR/etc/theme.xsl

and use Nginx to proxy the site through that in an XSLT module; this
is much faster than using paster. It runs on Mac and Linux, so long as
it can build against `libxml2` and `libxslt`.

Since we've built a custom patched nginx, our config and log files are
local to this application's build directory. The configs are at::

  $THISDIR/etc/nginx-dev.conf
  $THISDIR/etc/nginx.conf

And the PID and log files::

  $THISIDR/var/nginx.pid
  $THISDIR/var/log/nginx-access.log
  $THISDIR/var/log/nginx-error.log

In production, we'll need to configure `logrotate` to trim these logs,
rather than looking for them in the system's normal /var/logs/
directory.


Docker: build, run, curl, stop
==============================

We can build and run a container, test it with curl, then stop and remove it::

  make docker
  make docker_run
  make docker_test
  make docker_curl
  make docker_stop

The docker_run maps the container's nginx on port 80 to the docker
server's port 5000 just like paster and fullstack nginx.

The `docker_curl` command currently assumes you're on a Mac and using
`boot2docker`. This should be fixed later.



