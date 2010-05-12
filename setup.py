#!/usr/bin/env python

from setuptools import setup
import marrie

setup(
    name='marrie',
    version = marrie.__version__,
    license = marrie.__license__,
    description = marrie.__description__,
    author = marrie.__author__,
    author_email = marrie.__email__,
    url = marrie.__url__,
    py_modules = ['marrie'],
    entry_points = {
        'console_scripts': ['marrie = marrie:main']
    },
)
