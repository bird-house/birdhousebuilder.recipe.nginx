*****************************
birdhousebuilder.recipe.nginx
*****************************

.. contents::

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

The recipe requires that Anaconda is already installed. It assumes that the default Anaconda location is in your home directory ``~/anaconda``. Otherwise you need to set the ``ANACONDA_HOME`` environment variable or the Buildout option ``anaconda-home``.

The recipe will install the ``nginx`` package from a conda channel in a conda enviroment named ``birdhouse``. The location of the birdhouse environment is ``.conda/envs/birdhouse``. It deploys a Nginx site configuration for your application. The configuration will be deployed in ``~/.conda/envs/birdhouse/etc/nginx/conf.d/myapp.conf``. Nginx can be started with ``~/.conda/envs/birdhouse/etc/init.d/nginx start``.

The recipe depends on ``birdhousebuilder.recipe.conda``.

Supported options
=================

This recipe supports the following options:

``anaconda-home``
   Buildout option with the root folder of the Anaconda installation. Default: ``$HOME/anaconda``.
   The default location can also be set with the environment variable ``ANACONDA_HOME``. Example::

     export ANACONDA_HOME=/opt/anaconda

   Search priority is:

   1. ``anaconda-home`` in ``buildout.cfg``
   2. ``$ANACONDA_HOME``
   3. ``$HOME/anaconda``

``input``
   The path to a `Mako`_ template with a Nginx configuration for your application.

``sites``
   The name of your application.

``organization`` 
   The organization name for the certificate. Default: ``Birdhouse``

``organization_unit``
   The organization unit for the certificate. Default: ``Demo`` 

All additional options can be used as parameters in your Nginx site configuration. The ``anaconda-home`` Path is available as ``prefix`` parameter.


Example usage
=============

The following example ``buildout.cfg`` installs Nginx with a site configuration for ``myapp``::

  [buildout]
  parts = myapp_nginx

  anaconda-home = /home/myself/anaconda

  [myapp_nginx]
  recipe = birdhousebuilder.recipe.nginx
  input = ${buildout:directory}/templates/myapp_nginx.conf
  sites = myapp

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



