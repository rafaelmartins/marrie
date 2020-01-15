#!/usr/bin/env python

from setuptools import setup
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(current_dir, 'README.rst')) as fp:
    long_description = fp.read()

setup(
    name='marrie',
    version='0.4',
    license='BSD',
    description=('A simple podcast client that runs on the Command Line '
                 'Interface.'),
    long_description=long_description,
    author='Rafael Goncalves Martins',
    author_email='rafael@rafaelmartins.eng.br',
    url='https://github.com/rafaelmartins/marrie',
    py_modules=['marrie'],
    install_requires=['feedparser >= 5.1.3'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
    ],
    entry_points={'console_scripts': ['marrie = marrie:main']},
)
