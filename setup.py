#!/usr/bin/env python
from os import environ

try:
    from setuptools import setup
except ImportError:
    from distutils import setup

setup(
        name='adbb',
        version=2,
        description="Object Oriented AniDB UDP Client Library",
        author="Winterbird",
        author_email="adbb@winterbird.org",
        url='https://github.com/winterbird-code/adbb',
        platforms=['any'],
        license= "GPLv3",
        install_requires=['SQLAlchemy'],
        packages=['adbb'],
        package_data = {
            'adbb': ['*.txt']
            })
