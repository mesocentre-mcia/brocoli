#! /usr/bin/env python

from setuptools import setup, find_packages

setup(name='brocoli',
      version='0.1.0',
      description='Browse Collection for iRODS',
      author='Pierre Gay',
      author_email='pierre.gay@u-bordeaux.fr',
      packages=find_packages('.', exclude=['*.tests']),
      scripts=['scripts/brocoli'],
      python_requires='>=2.7',
      install_requires=[
      'six>=1.10.0',
      'python-irodsclient>=0.6.0',
      ]
     )
