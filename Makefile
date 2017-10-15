# Simplify clean, virtualenv, build, run, etc

# Default target is to build the FE
all:	build

help:
	@echo "Front-end developer targets: clean, build, run, test, test_browser"
	@echo "Fullstack developer targets: clean, fullstack, fullstack_run, fullstack_test, fullstack_stop"
	@echo "Production targets:          clean, prod,      prod_run,      prod_test"
	@echo "Docker targets: docker, docker_start, docker_curl, docker_stop"
	@echo "If you just say 'make' it will run the 'build' target."
	@echo "\"make test\" should test paster, fullstack and docker runs, as they should all listen on 5000."
	@echo "You don't need to install or invoke the virtualenv, it's done for you."

# Prerequisites and targets used by all developers

clean:
	rm -rf .installed.cfg .tox .venv2 bin develop-eggs eggs etc parts var
	@if test -n "${VIRTUAL_ENV}" ; then echo "You should 'deactivate' your virtualenv" ; fi

virtualenv venv .venv2:
	@if test -n "${VIRTUAL_ENV}"; then echo "First 'deactivate' your virtualenv"; exit 1; fi
	@echo "Using python=`which python`"
	virtualenv --python=python .venv2
	.venv2/bin/pip install -U pip


# Front-end developer targets

build bin/paster: .venv2
	.venv2/bin/pip install -U -r requirements.txt
	.venv2/bin/buildout

test tox: .venv2 bin/paster
	.venv2/bin/tox

test_browser: .venv2/bin/python
	.venv2/bin/python tests/browser_tests.py 

run: bin/paster
	bin/paster serve local.ini

# Fullstack targets.
# Builds patched nginx and compiles theme to XSL file

fullstack_build fullstack bin/nginx: .venv2
	.venv2/bin/pip install -U -r requirements.txt
	.venv2/bin/buildout -c buildout-fullstack.cfg

fullstack_run: bin/nginx
	bin/nginx -c `pwd`/etc/nginx-dev.conf

fullstack_test: bin/nginx .venv2/bin/tox
	@echo "shouldn't this be the same as 'test'?"
	.venv2/bin/tox
	.venv2/bin/python tests/integration_tests.py 

fullstack_stop: bin/nginx
	bin/nginx -c `pwd`/etc/nginx-dev.conf -s stop

# Production write logrotate to /etc/ so can't use fullstack build

prod_build prod: .venv2
	.venv2/bin/pip install -U -r requirements.txt
	.venv2/bin/buildout -c buildout-prod.cfg

prod_run: bin/nginx
	bin/nginx

prod_run_fg: bin/nginx
	bin/nginx -g "daemon off;"

prod_test: bin/nginx .venv2/bin/tox
	.venv2/bin/tox
	.venv2/bin/python tests/integration_tests.py --port 80

# Below, we can only have one running container, TTTDIAZO
# and this is OK since we can only use the port once.

docker docker_build tttdiazo: Dockerfile
	docker build -t tttdiazo .

docker_run:
	docker run -d --name TTTDIAZO -p 5000:80 -t tttdiazo

# This `boot2docker ip` won't work on ubuntu, therefore not on CircleCI
# .venv/bin/tox
docker_test:
	.venv2/bin/python tests/integration_tests.py --hostname `boot2docker ip`

docker_curl:
	curl `boot2docker ip`:5000

docker_stop: 
	docker stop TTTDIAZO
	docker rm TTTDIAZO

