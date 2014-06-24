# -*- coding: utf-8 -*-
# Copyright (C)2014 DKRZ GmbH

"""Recipe conda"""

import os
from mako.template import Template

import zc.buildout
import birdhousebuilder.recipe.conda
import birdhousebuilder.recipe.supervisor

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))
templ_mkcert_script = Template(filename=os.path.join(os.path.dirname(__file__), "mkcert.sh"))

def makedirs(dirname):
    try:
        os.makedirs(dirname)
    except OSError:
        pass

class Nginx(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']
        self.anaconda_home = b_options.get('anaconda-home', '/opt/anaconda')
        self.options['prefix'] = self.anaconda_home

        self.ssl_subject = options.get('ssl_subject', "/C=DE/ST=Hamburg/L=Hamburg/O=Phoenix/CN=localhost")
        self.ssl_overwrite = options.query_bool('ssl_overwrite', default='false')
        self.input = options.get('input')
        self.sites = options.get('sites', name)

    def install(self):
        installed = []
        installed += list(self.install_nginx())
        installed += list(self.install_config())
        installed += list(self.install_cert())
        installed += list(self.install_program())
        installed += list(self.install_sites())
        return installed

    def install_nginx(self):
        script = birdhousebuilder.recipe.conda.Conda(
            self.buildout,
            self.name,
            {'pkgs': 'nginx'})

        makedirs( os.path.join(self.anaconda_home, 'etc', 'nginx') )
        makedirs( os.path.join(self.anaconda_home, 'var', 'cache', 'nginx') )
        makedirs( os.path.join(self.anaconda_home, 'var', 'log', 'nginx') )
        
        return script.install()
        
    def install_config(self):
        """
        install nginx main config file
        """
        result = templ_config.render(
            prefix=self.anaconda_home,
            )

        output = os.path.join(self.anaconda_home, 'etc', 'nginx', 'nginx.conf')
        makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)
        return [output]

    def install_cert(self):
        from subprocess import check_call

        cert = os.path.join(self.anaconda_home, "etc", "nginx", "phoenix.cert")
        if not os.path.exists(cert) or self.ssl_overwrite:
            cmd = templ_mkcert_script.render(
                cert=cert,
                ssl_subject=self.ssl_subject,
                )
            check_call(cmd, shell=True)
            return [cert]
        return []

    def install_program(self):
        script = birdhousebuilder.recipe.supervisor.Supervisor(
            self.buildout,
            self.name,
            {'program': 'nginx',
             'command': '%s/bin/nginx -c %s/etc/nginx/nginx.conf -g "daemon off;"' % (self.anaconda_home, self.anaconda_home),
             })
        return script.install()

    def install_sites(self):
        templ_sites = Template(filename=self.input)
        result = templ_sites.render(**self.options)

        output = os.path.join(self.anaconda_home, 'etc', 'nginx', 'conf.d', self.sites + '.conf')
        makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)
        return [output]
    
    def update(self):
        return self.install()

def uninstall(name, options):
    pass

