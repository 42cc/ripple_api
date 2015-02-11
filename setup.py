#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os.path import join, dirname
from setuptools import setup, find_packages

setup(
    name='django-ripple_api',
    version='0.0.31',
    packages=find_packages(),
    requires=['python (>= 2.7)', 'requests', 'django_model_utils'],
    install_requires=['requests<2.3.0', 'django-model-utils'],
    tests_require=['mock'],
    description='Python wrapper for the Ripple API',
    long_description=open(join(dirname(__file__), 'README.rst')).read(),
    author='42 Coffee Cups',
    author_email='contact@42cc.co',
    url='https://github.com/42cc/ripple_api',
    download_url='https://github.com/42cc/ripple_api/archive/master.zip',
    license='BSD License',
    keywords=['ripple', 'api'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
    ],
)
