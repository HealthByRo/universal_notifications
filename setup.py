#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import re

from setuptools import setup


def local_open(fname):
    return open(os.path.join(os.path.dirname(__file__), fname))


def read_file(f):
    return io.open(f, 'r', encoding='utf-8').read()


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


def get_package_data(package):
    """
    Return all files under the root package, that are not in a
    package themselves.
    """
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not os.path.exists(os.path.join(dirpath, '__init__.py'))]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename)
                          for filename in filenames])
    return {package: filepaths}


version = get_version('universal_notifications')


requirements = local_open('requirements/requirements-base.txt')
required_to_install = [dist.strip() for dist in requirements.readlines()]


setup(
    name='universal_notifications',
    version=version,
    url='https://github.com/ArabellaTech/universal_notifications',
    license='MIT',
    description='High-level framework for notifications',
    long_description=read_file('README.rst'),
    author='Pawel Krzyzaniak',
    author_email='pawelk@arabel.la',
    packages=get_packages('universal_notifications'),
    package_data=get_package_data('universal_notifications'),
    zip_safe=False,
    install_requires=required_to_install,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
