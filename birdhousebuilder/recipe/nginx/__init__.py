# -*- coding: utf-8 -*-

"""Recipe nginx"""

import os
from mako.template import Template

import zc.buildout
from birdhousebuilder.recipe import conda, supervisor

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))

def generate_cert(out, org, org_unit, hostname):
    """
    Generates self signed certificate for https connections.

    Returns True on success.
    """
    from OpenSSL import crypto
    from uuid import uuid4
    try:
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
        import os, stat
        os.chmod(out, stat.S_IRUSR|stat.S_IWUSR)
    except:
        return False
    else:
        return True

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']

        self.prefix = self.options.get('prefix', conda.prefix())
        self.options['prefix'] = self.prefix
        self.options['hostname'] = self.options.get('hostname', 'localhost')
        self.options['organization'] = self.options.get('organization', 'Birdhouse')
        self.options['organization_unit'] = self.options.get('organization_unit', 'Demo')

        self.input = options.get('input')
        self.options['sites'] = self.options.get('sites', name)
        self.sites = self.options['sites']

    def install(self):
        installed = []
        installed += list(self.install_nginx())
        installed += list(self.install_cert())
        installed += list(self.install_config())
        installed += list(self.setup_service())
        installed += list(self.install_sites())
        return tuple()

    def install_nginx(self):
        script = conda.Recipe(
            self.buildout,
            self.name,
            {'pkgs': 'nginx openssl pyopenssl'})

        conda.makedirs( os.path.join(self.prefix, 'etc', 'nginx') )
        conda.makedirs( os.path.join(self.prefix, 'var', 'cache', 'nginx') )
        conda.makedirs( os.path.join(self.prefix, 'var', 'log', 'nginx') )
        
        return script.install()

    def install_cert(self):
        certfile = os.path.join(self.prefix, 'etc', 'nginx', 'cert.pem')
        if generate_cert(
                out=certfile,
                org=self.options.get('organization'),
                org_unit=self.options.get('organization_unit'),
                hostname=self.options.get('hostname')):
            return [certfile]
        else:
            return []
    
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
        self.install_cert()
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

