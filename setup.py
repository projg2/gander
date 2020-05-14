#!/usr/bin/env python
# (c) 2020 Michał Górny
# 2-clause BSD license

from setuptools import setup

from gander import __version__


setup(
    name='gander',
    version=__version__,
    description='Statistic submission client for Goose',

    author='Michał Górny',
    author_email='mgorny@gentoo.org',
    license='BSD',
    url='http://github.com/mgorny/gander',

    packages=['gander'],
    entry_points={
        'console_scripts': [
            'gander=gander.cli:setuptools_main',
        ],
    },

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
    ]
)
