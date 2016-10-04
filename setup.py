#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import re

from setuptools import setup


def read_md(f):
    return io.open(f, 'r', encoding='utf-8').read()


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


version = get_version('universal_notifications')


setup(
    name='universal_notifications',
    version=version,
    url='https://github.com/ArabellaTech/universal_notifications',
    license='Proprietary',
    description='High-level framework for notifications',
    long_description=read_md('README.md'),
    author='Pawel Krzyzaniak',
    author_email='pawelk@arabel.la',
    packages=['universal_notifications'],
    include_package_data=True,
    install_requires=[],
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
