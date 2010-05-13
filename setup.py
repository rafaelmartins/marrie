#!/usr/bin/env python

from setuptools import setup
import marrie
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(current_dir, 'README')) as fp:
    long_description = fp.read()

setup(
    name='marrie',
    version = marrie.__version__,
    license = marrie.__license__,
    description = marrie.__description__,
    long_description = long_description,
    author = marrie.__author__,
    author_email = marrie.__email__,
    url = marrie.__url__,
    py_modules = ['marrie'],
    entry_points = {
        'console_scripts': ['marrie = marrie:main']
    },
)
