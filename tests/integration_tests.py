#!/usr/bin/env python
# Copyright (c) 2016 V! Studios.
"""
Integration tests run by CircleCI after unit & functional tests are finished.

Queries a Diazo server running on the host to ensure a set of target endpoints return 200's.
Exits with status code 0 if all return 200's, else status code 1.
"""
import argparse
import logging
import os
import sys

from requests import get

URL_FILE_NAME = 'integration_tests_urls.txt'
DEFAULT_PORT = 5000
DEFAULT_HOST = 'localhost'

# Start log.
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(os.path.basename(__file__))
log.setLevel(logging.INFO)


def init_parser():
    """Return a configured arg parser."""
    parser = argparse.ArgumentParser(
        description="Run integration tests against a Diazo server."
    )
    parser.add_argument(
        '-H', '--hostname',
        default=DEFAULT_HOST,
        help=("Diazo server's hostname. Default: {}.".format(DEFAULT_HOST)),
    )
    parser.add_argument(
        '-P', '--port',
        default=DEFAULT_PORT,
        help=("Diazo server's port. Default: {}.".format(DEFAULT_PORT)),
    )
    return parser


def main(args):
    url_root = 'http://{}:{}'.format(args.hostname, args.port)
    # Read URL's out of the config file.
    tests_dir = os.path.dirname(__file__)
    with open(os.path.join(tests_dir, URL_FILE_NAME), 'r') as _f:
        urls = [i.strip('\n') for i in _f.readlines()]
    # For each URL, make a GET request.
    #   If any response is not a 200, note that in the log and mark this run as a failure.
    all_200 = True
    for url in urls:
        status_code = get(url_root + url).status_code
        if status_code != 200:
            log.warn('Got non-200 status code {} from {}.'.format(status_code, url))
            all_200 = False
    # If any responses weren't 200's, exit with status 1.
    if all_200 == False:
        log.error("Not all responses were 200's.")
        sys.exit(1)
    # Check sitemap.xml is text/xml, not rethemed as HTML
    res = get(url_root + '/sitemap.xml')
    ct = res.headers['content-type']
    if ct != 'text/xml':
        log.error('sitemap.xml not text/html but "{}"'.format(ct))
        sys.exit(1)
    # Else, exit with status 0.
    log.debug("All responses were 200's.")
    sys.exit(0)


if __name__ == '__main__':
    # Parse args.
    parser = init_parser()
    args = parser.parse_args()
    # Run.
    main(args)
