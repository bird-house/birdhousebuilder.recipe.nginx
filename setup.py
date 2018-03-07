# -*- coding: utf-8 -*-
"""
This module contains the tool of birdhousebuilder.recipe.nginx
"""
from setuptools import find_packages
from setuptools import setup

name = 'birdhousebuilder.recipe.nginx'

version = '0.3.7'
description = 'A Buildout recipe to install and configure Nginx with conda.'
long_description = (
    open('README.rst').read() + '\n' +
    open('AUTHORS.rst').read() + '\n' +
    open('CHANGES.rst').read()
)

entry_points = '''
[zc.buildout]
default = %(name)s:Recipe
[zc.buildout.uninstall]
default = %(name)s:uninstall
''' % globals()

reqs = ['setuptools',
        'zc.buildout',
        # -*- Extra requirements: -*-
        'mako',
        'pyopenssl',
        'zc.recipe.deployment',
        'birdhousebuilder.recipe.conda',
        'birdhousebuilder.recipe.supervisor',
        ],
tests_reqs = ['zope.testing', 'zc.buildout']

setup(name=name,
      version=version,
      description=description,
      long_description=long_description,
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          'Framework :: Buildout',
          'Intended Audience :: Developers',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'License :: OSI Approved :: BSD License',
      ],
      keywords='buildout recipe birdhouse nginx conda',
      author='Birdhouse',
      url='https://github.com/bird-house/birdhousebuilder.recipe.nginx',
      license='Apache License 2',
      install_requires=reqs,
      extras_require=dict(tests=tests_reqs),
      entry_points=entry_points,
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['birdhousebuilder', 'birdhousebuilder.recipe'],
      include_package_data=True,
      zip_safe=False,
      )
