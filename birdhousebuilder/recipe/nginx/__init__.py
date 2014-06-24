# -*- coding: utf-8 -*-
# Copyright (C)2014 DKRZ GmbH

"""Recipe conda"""

import os
from mako.template import Template

import birdhousebuilder.recipe.conda
import birdhousebuilder.recipe.supervisor

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))

class Nginx(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']
        self.anaconda_home = b_options.get('anaconda-home', '/opt/anaconda')

        self.program = options.get('program', name)

    def install(self):
        installed = []
        installed += list(self.install_nginx())
        installed += list(self.install_config())
        return installed

    def install_nginx(self):
        script = birdhousebuilder.recipe.conda.Conda(
            self.buildout,
            self.name,
            {'pkgs': 'nginx'})
        return script.install()
        
    def install_config(self):
        """
        install nginx main config file
        """
        result = templ_config.render(
            prefix=self.anaconda_home,
            )

        output = os.path.join(self.anaconda_home, 'etc', 'nginx', 'nginx.conf')
        try:
            os.makedirs(os.path.dirname(output))
        except OSError:
            pass
        
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

