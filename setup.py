#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import blackbird

setup(
    name='blackbird-aws-service-limits',
    version='0.1.0',
    description='Blackbird plugin AWS Service Limits.',
    author='Vagrants',
    author_email='vagrants@gmail.com',
    url='https://github.com/Vagrants/blackbird-aws-service-limits',
    install_requires=[
        'boto',
        'blackbird'
    ],
    tests_require=[
        'nose',
        'moto'
    ],
    classifiers=[
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]
)