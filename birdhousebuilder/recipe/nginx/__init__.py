# -*- coding: utf-8 -*-

"""Recipe nginx"""

import os
import stat
from shutil import copy2
from uuid import uuid4
from mako.template import Template
import logging

import zc.buildout
import zc.recipe.deployment

from birdhousebuilder.recipe import conda, supervisor


templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))
templ_cmd = Template(
    '${env_path}/sbin/nginx -p ${prefix} -c ${etc_prefix}/nginx/nginx.conf -g "daemon off;"')

def generate_cert(out, org, org_unit, hostname):
    """
    Generates self signed certificate for https connections.

    Returns True on success.
    """
    try:
        from OpenSSL import crypto
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
        cert.get_subject().O = org
        cert.get_subject().OU = org_unit
        cert.get_subject().CN = hostname
        sequence = int(uuid4().hex, 16)
        cert.set_serial_number(sequence)
        # valid right now
        cert.gmtime_adj_notBefore(0)
        # valid for 365 days
        cert.gmtime_adj_notAfter(31536000)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')
        # write to cert and key to same file
        open(out, "wt").write(
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        open(out, "at").write(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

        os.chmod(out, stat.S_IRUSR|stat.S_IWUSR)
    except:
        print("Certificate generation has failed!")
        return False
    else:
        return True

def make_dirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']

        self.options['name'] = self.options.get('name', self.name)
        self.name = self.options['name']

        self.logger = logging.getLogger(name)

        deployment = zc.recipe.deployment.Install(buildout, "nginx", {
                                                'prefix': self.options['prefix'],
                                                'user': self.options['user'],
                                                'etc-user': self.options['user']})
        deployment.install()
        
        self.options['etc_prefix'] = deployment.options['etc-prefix']
        self.options['var_prefix'] = deployment.options['var-prefix']
        self.options['etc-directory'] = deployment.options['etc-directory']
        self.options['lib_directory'] = deployment.options['lib-directory']
        self.options['log_directory'] = deployment.options['log-directory']
        self.options['cache_directory'] = deployment.options['cache-directory']
        self.prefix = self.options['prefix']

        self.env_path = conda.conda_env_path(buildout, options)
        self.options['env_path'] = self.env_path
        
        self.options['hostname'] = self.options.get('hostname', 'localhost')
        self.options['user'] = self.options.get('user', '')
        self.options['worker_processes'] = self.options.get('worker_processes', '1')
        self.options['keepalive_timeout'] = self.options.get('keepalive_timeout', '5s')
        self.options['sendfile'] = self.options.get('sendfile', 'off')
        self.options['organization'] = self.options.get('organization', 'Birdhouse')
        self.options['organization_unit'] = self.options.get('organization_unit', 'Demo')

        self.input = options.get('input')
        

    def install(self, update=False):
        installed = []
        installed += list(self.install_nginx(update))
        installed += list(self.install_cert(update))
        installed += list(self.install_config(update))
        installed += list(self.install_supervisor(update))
        installed += list(self.install_sites(update))
        return installed

    def install_nginx(self, update):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'nginx openssl pyopenssl cryptography'})

        return script.install(update=update)

    def install_cert(self, update):
        certfile = os.path.join(self.options['etc-directory'], 'cert.pem')
        if update:
            # Skip cert generation on update mode
            return []
        elif os.path.isfile(certfile):
            # Skip cert generation if file already exists.
            return []
        elif generate_cert(
                out=certfile,
                org=self.options.get('organization'),
                org_unit=self.options.get('organization_unit'),
                hostname=self.options.get('hostname')):
            return []
        else:
            return []
    
    def install_config(self, update):
        """
        install nginx main config file
        """
        text = templ_config.render(**self.options)
        conf_path = os.path.join(self.options['etc-directory'], 'nginx.conf')

        with open(conf_path, 'wt') as fp:
            fp.write(text)

        # copy additional files
        try:
            copy2(os.path.join(os.path.dirname(__file__), "mime.types"), conf_path)
        except:
            pass
        
        return [conf_path]

    def install_supervisor(self, update):
        # for nginx only set chmod_user in supervisor!
        script = supervisor.Recipe(
            self.buildout,
            self.name,
            {'prefix': self.options['prefix'],
             'user': self.options['user'],
             'chown': self.options.get('user', ''),
             'program': 'nginx',
             'command': templ_cmd.render(**self.options),
             'directory': '%s/sbin' % (self.env_path),
             })
        return script.install(update)

    def install_sites(self, update):
        templ_sites = Template(filename=self.input)
        text = templ_sites.render(**self.options)

        conf_path = os.path.join(self.options['etc-directory'], 'conf.d', self.name + '.conf')
        make_dirs(os.path.dirname(conf_path))
        
        with open(conf_path, 'wt') as fp:
            fp.write(text)
        return [conf_path]

    def update(self):
        return self.install(update=True)
    
    def upgrade(self):
        # clean up things from previous versions
        # TODO: this is not the correct way to do it
        pass

def uninstall(name, options):
    pass

