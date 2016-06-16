# -*- coding: utf-8 -*-

"""Recipe nginx"""

import os
import stat
from shutil import copy2
from uuid import uuid4
from mako.template import Template

import zc.buildout
from birdhousebuilder.recipe import conda, supervisor
from birdhousebuilder.recipe.conda import conda_envs, anaconda_home

import logging
logger = logging.getLogger(__name__)

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))
templ_cmd = Template(
    '${env_path}/sbin/nginx -p ${prefix} -c ${prefix}/etc/nginx/nginx.conf -g "daemon off;"')

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
        logger.exception("Certificate generation has failed!")
        return False
    else:
        return True

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']

        self.anaconda_home = b_options.get('anaconda-home', anaconda_home())
        b_options['anaconda-home'] = self.anaconda_home

        self.prefix = self.options.get('prefix', conda.prefix())
        self.options['prefix'] = self.prefix

        self.env = options.get('env', b_options.get('conda-env'))
        self.env_path = conda_envs(self.anaconda_home).get(self.env, self.anaconda_home)
        self.options['env_path'] = self.env_path
        
        self.options['hostname'] = self.options.get('hostname', 'localhost')
        self.options['user'] = self.options.get('user', '')
        self.options['worker_processes'] = self.options.get('worker_processes', '1')
        self.options['keepalive_timeout'] = self.options.get('keepalive_timeout', '5s')
        self.options['sendfile'] = self.options.get('sendfile', 'off')
        self.options['organization'] = self.options.get('organization', 'Birdhouse')
        self.options['organization_unit'] = self.options.get('organization_unit', 'Demo')

        self.input = options.get('input')
        self.options['sites'] = self.options.get('sites', name)
        self.sites = self.options['sites']

    def install(self, update=False):
        installed = []
        installed += list(self.install_nginx(update))
        installed += list(self.install_cert(update))
        installed += list(self.install_config(update))
        installed += list(self.setup_service(update))
        installed += list(self.install_sites(update))
        return installed

    def install_nginx(self, update):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'nginx openssl pyopenssl cryptography'})

        conda.makedirs( os.path.join(self.prefix, 'etc', 'nginx') )
        conda.makedirs( os.path.join(self.prefix, 'var', 'cache', 'nginx') )
        conda.makedirs( os.path.join(self.prefix, 'var', 'log', 'nginx') )

        if update:
            return script.update()
        else:
            return script.install()

    def install_cert(self, update):
        certfile = os.path.join(self.prefix, 'etc', 'nginx', 'cert.pem')
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
        result = templ_config.render(**self.options)

        config_path = os.path.join(self.prefix, 'etc', 'nginx')
        output = os.path.join(config_path, 'nginx.conf')
        conda.makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)

        # copy additional files
        try:
            copy2(os.path.join(os.path.dirname(__file__), "mime.types"), config_path)
        except:
            pass
        
        return [output]

    def setup_service(self, update):
        # for nginx only set chmod_user in supervisor!
        script = supervisor.Recipe(
            self.buildout,
            self.name,
            {'chown': self.options.get('user', ''),
             'program': 'nginx',
             'command': templ_cmd.render(**self.options),
             'directory': '%s/sbin' % (self.env_path),
             })
        return script.install(update)

    def install_sites(self, update):
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
        return self.install(update=True)
    
    def upgrade(self):
        # clean up things from previous versions
        # TODO: this is not the correct way to do it
        #self.remove_start_stop()
        pass

def uninstall(name, options):
    pass

