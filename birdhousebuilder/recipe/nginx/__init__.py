# -*- coding: utf-8 -*-
# Copyright (C)2014 DKRZ GmbH

"""Recipe conda"""

import os
from mako.template import Template

import birdhousebuilder.recipe.conda

templ_config = Template(
"""
[unix_http_server]
file=${prefix}/var/run/supervisor.sock

[inet_http_server]
port = ${host}:${port}

[supervisord]
childlogdir=${prefix}/var/log/supervisor
logfile=${prefix}/var/log/supervisor/supervisord.log
pidfile=${prefix}/var/run/supervisord.pid
logfile_maxbytes=50MB
logfile_backups=10
loglevel=info
nodaemon=false
minfds=1024
minprocs=200

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///${prefix}/var/run/supervisor.sock

[include]
files = conf.d/*.conf
"""
)

templ_program = Template(
"""
[program:${program}]
command=${command}
directory=${directory}
priority=${priority}
autostart=true
autorestart=true
redirect_stderr=true
environment=${environment}
"""
)

templ_start_stop = Template(filename=os.path.join(os.path.dirname(__file__), "supervisord"))

class Nginx(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']
        self.anaconda_home = b_options.get('anaconda-home', '/opt/anaconda')
        bin_path = os.path.join(self.anaconda_home, 'bin')
        lib_path = os.path.join(self.anaconda_home, 'lib')
        self.conda_channels = b_options.get('conda-channels')

        self.host = b_options.get('supervisor-host', 'localhost')
        self.port = b_options.get('supervisor-port', '9001')
        
        self.program = options.get('program', name)
        self.command = options.get('command')
        self.directory =  options.get('directory', bin_path)
        self.priority = options.get('priority', '10')
        self.environment = options.get('environment',
                                       'PATH="%s",LD_LIBRARY_PATH="%s"' % (bin_path, lib_path))

    def install(self):
        installed = []
        installed += list(self.install_supervisor())
        installed += list(self.install_config())
        installed += list(self.install_program())
        installed += list(self.install_start_stop())
        return installed

    def install_supervisor(self):
        script = birdhousebuilder.recipe.conda.Conda(
            self.buildout,
            self.name,
            {'pkgs': 'supervisor'})
        return script.install()
        
    def install_config(self):
        """
        install supervisor main config file
        """
        result = templ_config.render(
            prefix=self.anaconda_home,
            host=self.host,
            port=self.port)

        output = os.path.join(self.anaconda_home, 'etc', 'supervisor', 'supervisord.conf')
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
        
    def install_program(self):
        """
        install supervisor program config file
        """
        result = templ_program.render(
            program=self.program,
            command=self.command,
            directory=self.directory,
            priority=self.priority,
            environment=self.environment)

        output = os.path.join(self.anaconda_home, 'etc', 'supervisor', 'conf.d', self.program + '.conf')
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

    def install_start_stop(self):
        result = templ_start_stop.render(
            prefix=self.anaconda_home)
        output = os.path.join(self.anaconda_home, 'etc', 'init.d', 'supervisord')
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

