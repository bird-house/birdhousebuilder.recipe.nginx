*****************************
birdhousebuilder.recipe.nginx
*****************************

.. image:: https://travis-ci.org/bird-house/birdhousebuilder.recipe.nginx.svg?branch=master
   :target: https://travis-ci.org/bird-house/birdhousebuilder.recipe.nginx
   :alt: Travis Build

Introduction
************

``birdhousebuilder.recipe.nginx`` is a `Buildout`_ recipe to install `Nginx`_ from an `Anaconda`_ channel and to deploy a site configuration for your application.
This recipe is used by the `Birdhouse`_ project. 

.. _`Buildout`: http://buildout.org/
.. _`Anaconda`: http://continuum.io/
.. _`Nginx`: http://nginx.org/
.. _`Mako`: http://www.makotemplates.org
.. _`Birdhouse`: http://bird-house.github.io

Usage
*****

The recipe requires that Anaconda is already installed. You can use the buildout option ``anaconda-home`` to set the prefix for the anaconda installation. Otherwise the environment variable ``CONDA_PREFIX`` (variable is set when activating a conda environment) is used as conda prefix. 

The recipe will install the ``nginx`` package from a conda channel in a conda enviroment defined by ``CONDA_PREFIX``. The intallation folder is given by the ``prefix`` buildout option. It deploys a Nginx site configuration for your application. The configuration will be deployed in ``${prefix}/etc/nginx/conf.d/myapp.conf``. Nginx can be started with ``${prefix}/etc/init.d/nginx start``.

The recipe depends on ``birdhousebuilder.recipe.conda`` and ``zc.recipe.deployment``.

Supported options
=================

This recipe supports the following options:

**anaconda-home**
   Buildout option pointing to the root folder of the Anaconda installation. Default: ``$HOME/anaconda``.

Buildout part options for the program section:

**prefix**
  Deployment option to set the prefix of the installation folder. Default: ``/``

**user**
  Deployment option to set the run user.

**etc-user**
  Deployment option to set the user of the ``/etc`` directory. Default: ``root``

**name**
   The name of your application.

**input**
   The path to a `Mako`_ template with a Nginx configuration for your application.

**worker-processes**
   The number of worker processes started (use ``auto`` for dynamic value). Default: 1

**keepalive-timeout**
   Timeout during keep-alive client connection will stay open on the server side. Default: 5s

**organization** 
   The organization name for the certificate. Default: ``Birdhouse``

**organization-unit**
   The organization unit for the certificate. Default: ``Demo`` 

All additional options can be used as parameters in your Nginx site configuration.


Example usage
=============

The following example ``buildout.cfg`` installs Nginx with a site configuration for ``myapp``::

  [buildout]
  parts = myapp_nginx

  anaconda-home = /opt/anaconda

  [myapp_nginx]
  recipe = birdhousebuilder.recipe.nginx
  name = myapp
  prefix = /
  user = www-data
  input = ${buildout:directory}/templates/myapp_nginx.conf
 
  hostname =  localhost
  port = 8081

An example Mako template for your Nginx configuration could look like this::

  upstream myapp {
    server unix:///tmp/myapp.socket fail_timeout=0;
  }

  server {
    listen ${port};
    server_name ${hostname};

    root ${prefix}/var/www;      
    index index.html index.htm;

    location / {
      # checks for static file, if not found proxy to app
      try_files $uri @proxy_to_phoenix;
    }

    location @proxy_to_phoenix {
        proxy_pass http://myapp;
    }
  }



