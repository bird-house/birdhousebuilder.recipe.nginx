# -*- coding: utf-8 -*-

"""Recipe nginx"""

import os
from mako.template import Template

import zc.buildout
from birdhousebuilder.recipe import conda, supervisor

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']

        self.prefix = self.options.get('prefix', conda.prefix())
        self.options['prefix'] = self.prefix

        self.options['hostname'] = self.options.get('hostname', 'localhost')
        self.options['proxy_enabled'] = self.options.get('proxy-enabled', 'false')

        self.input = options.get('input')
        self.options['sites'] = self.options.get('sites', name)
        self.sites = self.options['sites']

    def install(self):
        installed = []
        installed += list(self.install_nginx())
        installed += list(self.install_config())
        installed += list(self.setup_service())
        installed += list(self.install_sites())

        #self.upgrade()
        
        return tuple()

    def install_nginx(self):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'nginx'})

        conda.makedirs( os.path.join(self.prefix, 'etc', 'nginx') )
        conda.makedirs( os.path.join(self.prefix, 'var', 'cache', 'nginx') )
        conda.makedirs( os.path.join(self.prefix, 'var', 'log', 'nginx') )
        
        return script.install()
        
    def install_config(self):
        """
        install nginx main config file
        """
        result = templ_config.render(**self.options)

        output = os.path.join(self.prefix, 'etc', 'nginx', 'nginx.conf')
        conda.makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)
        return [output]

    def setup_service(self):
        script = supervisor.Recipe(
            self.buildout,
            self.name,
            {'program': 'nginx',
             'command': '%s/sbin/nginx -p %s -c %s/etc/nginx/nginx.conf -g "daemon off;"' % (self.prefix, self.prefix, self.prefix),
             'directory': '%s/sbin' % (self.prefix),
             })
        return script.install()

    def install_sites(self):
        templ_sites = Template(filename=self.input)
        result = templ_sites.render(**self.options)

        output = os.path.join(self.prefix, 'etc', 'nginx', 'conf.d', self.sites + '.conf')
        conda.makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)
        return [output]

    def remove_start_stop(self):
        output = os.path.join(self.prefix, 'etc', 'init.d', 'nginx')
        
        try:
            os.remove(output)
        except OSError:
            pass
        return [output]
    
    def update(self):
        #self.install_nginx()
        self.install_config()
        self.setup_service()
        self.install_sites()
        return tuple()

    def upgrade(self):
        # clean up things from previous versions
        # TODO: this is not the correct way to do it
        self.remove_start_stop()

def uninstall(name, options):
    pass

