#!/usr/bin/env python
# encoding: utf-8
"""
tempoiq-python/setup.py

Copyright (c) 2012-2015 TempoDB Inc. All rights reserved.
"""

import re
from setuptools import setup


install_requires = [
    'python-dateutil >=2.4',
    'requests >=2.5, !=2.6.1, !=2.6.2',
    'simplejson >=3.6',
    'pytz',
    'sphinx'
]

tests_require = [
    'mock',
    'unittest2',
]

version = ''
with open('tempoiq/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)
if not version:
    raise RuntimeError('Cannot find version information')

setup(
    name="tempoiq",
    version=version,
    author="TempoIQ Inc",
    author_email="aaron.brenzel@tempoiq.com",
    url="http://github.com/tempoiq/tempoiq-python/",
    description="Python bindings for the TempoIQ API",
    packages=["tempoiq", "tempoiq.temporal", "tempoiq.protocol",
              "tempoiq.protocol.query"],
    long_description="Python bindings for the TempoIQ API",
    dependency_links=[
    ],
    setup_requires=['nose>=1.0'],
    install_requires=install_requires,
    tests_require=tests_require,
)
