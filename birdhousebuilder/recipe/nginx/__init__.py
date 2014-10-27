# -*- coding: utf-8 -*-

"""Recipe nginx"""

import os
from mako.template import Template

import zc.buildout
from birdhousebuilder.recipe import conda

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))
templ_proxy_config = Template(filename=os.path.join(os.path.dirname(__file__), "proxy.conf"))
templ_start_stop = Template(filename=os.path.join(os.path.dirname(__file__), "nginx"))

def _new_serial(ca_name, CN):
    '''
    Return a serial number in hex using md5sum, based upon the ca_name and
    CN values
  
    ca_name
        name of the CA
    CN
        common name in the request
    '''
    import hashlib
    import time
    
    hashnum = int(
            hashlib.md5(
                '{0}_{1}_{2}'.format(
                    ca_name,
                    CN,
                    int(time.time()))
                ).hexdigest(),
            16
            )
    return hashnum

def create_self_signed_cert(cert_dir, app_name='myapp', subject={}):
    """
    If datacard.crt and datacard.key don't exist in cert_dir, create a new
    self-signed cert and keypair and write them into that directory.
    """

    from OpenSSL import crypto, SSL
    import os

    cert_file = os.path.join(cert_dir, app_name + ".cert")
    key_file = os.path.join(cert_dir, app_name + ".key")

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
            
        # create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = subject.get('C', "DE")
        cert.get_subject().O = subject.get('O', "my company")
        cert.get_subject().OU = subject.get('OU', "my organization")
        cert.get_subject().CN = subject.get('CN', "localhost")
        cert.set_serial_number(_new_serial(app_name, subject.get('CN', 'localhost')))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        open(cert_file, "wt").write(
            crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        open(key_file, "wt").write(
            crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

    return [cert_file, key_file]

class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']
        self.prefix = b_options.get('anaconda-home', conda.anaconda_home())
        self.options['prefix'] = self.prefix
        self.options['user'] = self.options.get('user', 'www-data')
        self.options['group'] = self.options.get('group', 'www-data')
        self.options['hostname'] = self.options.get('hostname', 'localhost')
        self.options['http_port'] = self.options.get('http_port', '8081')
        self.options['wps_url'] = self.options.get('wps_url', 'http://localhost:8091/wps')
        self.options['thredds_url'] = self.options.get('thredds_url', 'http://localhost:8080/thredds')
        self.options['proxy_enabled'] = self.options.get('proxy-enabled', 'false')
        self.options['superuser_enabled'] = self.options.get('superuser-enabled', 'false')
        self.master =  conda.as_bool(self.options.get('master', 'false'))
        self.proxy_enabled = conda.as_bool(self.options['proxy_enabled'])

        self.input = options.get('input')
        self.options['sites'] = self.options.get('sites', name)
        self.sites = self.options['sites']

    def install(self):
        installed = []
        installed += list(self.install_nginx())
        if self.master:
            installed += list(self.install_config())
        if self.master and self.proxy_enabled:
            installed += list(self.install_proxy_config())
            installed += list(self.install_cert())
        #installed += list(self.setup_service())
        installed += list(self.install_start_stop())
        installed += list(self.install_sites())
        return installed

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

    def install_proxy_config(self):
        result = templ_proxy_config.render(**self.options)

        output = os.path.join(self.prefix, 'etc', 'nginx', 'conf.d', 'proxy.conf')
        conda.makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)
        return [output]

    def install_cert(self):
        cert_dir = os.path.join(self.prefix, "etc", "nginx")
        subject = dict(
            C=self.options.get('country', 'DE'),
            O=self.options.get('company', 'my company'),
            OU=self.options.get('organisation', 'my organisation'),
            CN=self.options.get('hostname'))
        create_self_signed_cert(cert_dir=cert_dir, app_name=self.sites, subject=subject)
        return []

    ## def setup_service(self):
    ##     script = supervisor.Recipe(
    ##         self.buildout,
    ##         self.name,
    ##         {'program': 'nginx',
    ##          'command': '%s/bin/nginx -c %s/etc/nginx/nginx.conf -g "daemon off;"' % (self.prefix, self.prefix),
    ##          })
    ##     return script.install()

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

    def install_start_stop(self):
        result = templ_start_stop.render(
            prefix=self.prefix)
        output = os.path.join(self.prefix, 'etc', 'init.d', 'nginx')
        conda.makedirs(os.path.dirname(output))
        
        try:
            os.remove(output)
        except OSError:
            pass

        with open(output, 'wt') as fp:
            fp.write(result)
            os.chmod(output, 0o755)
        return [output]
    
    def update(self):
        return self.install()

def uninstall(name, options):
    pass

