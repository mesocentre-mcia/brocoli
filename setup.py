#! /usr/bin/env python

from setuptools import setup, find_packages

setup(name='catabrowse',
      version='0.1',
      description='catalog browser application',
      author='Pierre Gay',
      author_email='pierre.gay@u-bordeaux.fr',
      packages=find_packages('.', exclude=['*.tests']),
      scripts=['scripts/catabrowse_viewer.py'],
      python_requires='>=2.7',
      install_requires=[
      'six>=1.10.0',
      'python-irodsclient',
      ]
     )
