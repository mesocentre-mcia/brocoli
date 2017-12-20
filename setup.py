#! /usr/bin/env python

# ideas stolen from https://github.com/jgehrcke/python-cmdline-bootstrap

import re

from setuptools import setup, find_packages

version = re.search(
    '^__version__\s*=\s*\'(.*)\'',
    open('brocoli/brocoli.py').read(),
    re.M
    ).group(1)


with open("README.rst", "rb") as f:
    long_descr = f.read().decode("utf-8")

setup(name='brocoli',
      version=version,
      description='Browse Collections for iRODS',
      long_description=long_descr,
      author='Pierre Gay',
      author_email='pierre.gay@u-bordeaux.fr',
      url='https://github.com/mesocentre-mcia/brocoli',
      packages=find_packages('.', exclude=['*.tests']),
      entry_points = {
        "console_scripts": ['brocoli = brocoli.brocoli:main']
        },
      python_requires='>=2.7',
      keywords=['irods', 'tkinter'],
      classifiers=[
        'License :: OSI Approved :: BSD License',
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: POSIX :: Linux',
        'Topic :: Desktop Environment :: File Managers',
      ],
      install_requires=[
      'six>=1.10.0',
      'python-irodsclient>=0.7.0',
      ]
     )
