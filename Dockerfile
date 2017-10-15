# Use .dockerignore to skip crap
# docker build -t tttdiazo .
# docker run -p 5000:80 -t tttdiazo
# curl `boot2docker ip`:5000

FROM ubuntu:14.04
MAINTAINER Chris Shenton <chris@v-studios.com>

EXPOSE 80

# Install libxml2, libxslt and friends so buildout doesn't have to build it.

RUN apt-get update && apt-get install -y git python python-setuptools python-dev build-essential libxml2-dev libxslt-dev zlib1g-dev libpcre3-dev libffi-dev libssl-dev


RUN easy_install pip && pip install virtualenv

# Use same dir as on Prod Ubuntu so logrotate will work.
WORKDIR /var/app

COPY Makefile buildout-base.cfg buildout-fullstack.cfg buildout-prod.cfg requirements.txt rules.xml ./
COPY theme ./theme/
COPY templates ./templates/

RUN make prod_build

# Run in foreground so container doesn't exit

CMD ["make", "prod_run_fg"]
