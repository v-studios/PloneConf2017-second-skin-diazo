#!/usr/bin/env python
"""TTTDiazo package setup.

Copyright (c) 2016 V! Studios.
"""
import os

from pip.req import parse_requirements
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'VERSION.txt')) as f:
    VERSION = f.read().strip()

# use pip to parse the requirements.txt files into lists.
reqs = [str(i.req) for i in parse_requirements('requirements.txt',
                                               session=False)]

setup(name='tttdiazo',
      version=VERSION,
      description='tttdiazo',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      author='',
      author_email='',
      url='',
      keywords='web',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=reqs,
      test_suite='tttdiazo',
      )
