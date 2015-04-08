#!/usr/bin/env python
# encoding: utf-8
"""
tempoiq-python/setup.py

Copyright (c) 2012-2015 TempoDB Inc. All rights reserved.
"""

from setuptools import setup


install_requires = [
    'python-dateutil',
    'requests>=1.0',
    'simplejson',
    'pytz',
    'sphinx'
]

tests_require = [
    'mock',
    'unittest2',
]

setup(
    name="tempoiq",
    version="1.0.3",
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
