# -*- coding: utf-8 -*-

"""Recipe nginx"""

import os
import pwd
import stat
from shutil import copy2
from uuid import uuid4
from mako.template import Template
import logging

import zc.buildout
import zc.recipe.deployment
from zc.recipe.deployment import Configuration
from zc.recipe.deployment import make_dir
import birdhousebuilder.recipe.conda
from birdhousebuilder.recipe import supervisor
from birdhousebuilder.recipe.nginx._compat import urlretrieve

templ_config = Template(filename=os.path.join(os.path.dirname(__file__), "nginx.conf"))
templ_cmd = Template(
    '${conda_prefix}/sbin/nginx -p ${prefix} -c ${etc_prefix}/nginx/nginx.conf -g "daemon off;"')


def make_dirs(name, user, mode=0o755):
    etc_uid, etc_gid = pwd.getpwnam(user)[2:4]
    created = []
    make_dir(name, etc_uid, etc_gid, mode, created)


def generate_cert(out, org, org_unit, hostname, key_length=1024):
    """
    Generates self signed certificate for https connections.

    Returns True on success.
    """
    try:
        from OpenSSL import crypto
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, key_length)
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
        # TODO: fix permissions  ... nginx is run by unpriviledged user.
        # os.chmod(out, stat.S_IRUSR|stat.S_IWUSR)
    except Exception:
        print("Certificate generation has failed!")
        return False
    else:
        return True


class Recipe(object):
    """This recipe is used by zc.buildout"""

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        b_options = buildout['buildout']

        self.options['name'] = self.options.get('name', self.name)
        self.name = self.options['name']

        self.logger = logging.getLogger(name)

        # deployment layout
        def add_section(section_name, options):
            if section_name in buildout._raw:
                raise KeyError("already in buildout", section_name)
            buildout._raw[section_name] = options
            buildout[section_name]  # cause it to be added to the working parts

        self.deployment_name = self.name + "-nginx-deployment"
        self.deployment = zc.recipe.deployment.Install(buildout, self.deployment_name, {
            'name': "nginx",
            'prefix': self.options['prefix'],
            'user': self.options['user'],
            'etc-user': self.options['etc-user']})
        add_section(self.deployment_name, self.deployment.options)

        self.options['etc_user'] = self.options['etc-user']
        self.options['etc-prefix'] = self.options['etc_prefix'] = self.deployment.options['etc-prefix']
        self.options['var-prefix'] = self.options['var_prefix'] = self.deployment.options['var-prefix']
        self.options['etc-directory'] = self.options['etc_directory'] = self.deployment.options['etc-directory']
        self.options['lib-directory'] = self.options['lib_directory'] = self.deployment.options['lib-directory']
        self.options['log-directory'] = self.options['log_directory'] = self.deployment.options['log-directory']
        self.options['run-directory'] = self.options['run_directory'] = self.deployment.options['run-directory']
        self.options['cache-directory'] = self.options['cache_directory'] = self.deployment.options['cache-directory']
        self.prefix = self.options['prefix']

        # conda environment path
        self.options['env'] = self.options.get('env', '')
        self.options['pkgs'] = self.options.get('pkgs', 'nginx openssl pyopenssl cryptography')
        self.options['channels'] = self.options.get('channels', 'defaults birdhouse')
        self.conda = birdhousebuilder.recipe.conda.Recipe(self.buildout, self.name, {
            'env': self.options['env'],
            'pkgs': self.options['pkgs'],
            'channels': self.options['channels']})
        self.options['conda-prefix'] = self.options['conda_prefix'] = self.conda.options['prefix']

        # config options
        self.options['hostname'] = self.options.get('hostname', 'localhost')
        self.options['http-port'] = self.options['http_port'] = self.options.get('http-port', '80')
        self.options['https-port'] = self.options['https_port'] = self.options.get('https-port', '443')
        self.options['worker-processes'] = self.options['worker_processes'] = self.options.get('worker-processes', '1')
        self.options['keepalive-timeout'] = self.options['keepalive_timeout'] = \
            self.options.get('keepalive-timeout', '5s')
        self.options['sendfile'] = self.options.get('sendfile', 'off')
        self.options['organization'] = self.options.get('organization', 'Birdhouse')
        self.options['organization-unit'] = self.options.get('organization-unit', 'Demo')
        self.options['ssl-key-length'] = self.options['ssl_key_length'] = self.options.get('ssl-key-length', '1024')
        self.options['ssl-verify-client'] = self.options['ssl_verify_client'] = \
            self.options.get('ssl-verify-client', 'off')
        self.options['ssl-client-certificate'] = self.options['ssl_client_certificate'] = \
            self.options.get('ssl-client-certificate', 'esgf-ca-bundle.crt')
        self.options['ssl-client-certificate-url'] = self.options['ssl_client_certificate_url'] = \
            self.options.get(
                'ssl-client-certificate-url',
                'https://github.com/ESGF/esgf-dist/raw/master/installer/certs/esgf-ca-bundle.crt')

        self.input = options.get('input')

        # make nginx dirs
        make_dirs(self.options['etc-directory'], self.options['etc-user'], mode=0o755)
        for dirname in ['client', 'fastcgi', 'proxy', 'scgi', 'uwsgi']:
            make_dirs(os.path.join(self.options['etc-directory'], dirname), self.options['etc-user'], mode=0o755)
        # var folder
        make_dirs(self.options['var-prefix'], self.options['user'], mode=0o755)
        make_dirs(os.path.join(self.options['var-prefix'], 'run'), self.options['user'], mode=0o755)
        make_dirs(os.path.join(self.options['var-prefix'], 'tmp', 'nginx'), self.options['user'], mode=0o755)
        # make www folder
        make_dirs(os.path.join(self.options['var-prefix'], 'www'), self.options['user'], mode=0o755)

    def install(self, update=False):
        installed = []
        if not update:
            installed += list(self.deployment.install())
        installed += list(self.conda.install(update))
        installed += list(self.install_cert(update))
        installed += list(self.install_ca_bundle(update))
        installed += list(self.install_config(update))
        installed += list(self.install_supervisor(update))
        installed += list(self.install_sites(update))
        return installed

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
                org_unit=self.options.get('organization-unit'),
                hostname=self.options.get('hostname'),
                key_length=int(self.options.get('ssl-key-length'))):
            return []
        else:
            return []

    def install_ca_bundle(self, update):
        if self.options['ssl-verify-client'] in ['on', 'optional'] and \
                self.options.get('ssl-client-certificate-url', ''):
            ca_bundle_file = os.path.join(self.options['etc-directory'], self.options['ssl-client-certificate'])
            urlretrieve(
                self.options['ssl-client-certificate-url'],
                ca_bundle_file)
        return []

    def install_config(self, update):
        """
        install nginx main config file
        """
        text = templ_config.render(**self.options)
        config = Configuration(self.buildout, 'nginx.conf', {
            'deployment': self.deployment_name,
            'text': text})
        # copy additional files
        try:
            copy2(os.path.join(os.path.dirname(__file__), "mime.types"), self.options['etc-directory'])
        except Exception:
            pass
        return [config.install()]

    def install_supervisor(self, update):
        # for nginx only set chmod_user in supervisor!
        script = supervisor.Recipe(
            self.buildout,
            self.name + '-nginx',
            {'prefix': self.options['prefix'],
             'user': self.options['user'],
             'etc-user': self.options['etc-user'],
             'skip-user': True,
             'program': 'nginx',
             'command': templ_cmd.render(**self.options),
             'directory': '%s/sbin' % (self.options['conda-prefix']),
             })
        return script.install(update)

    def install_sites(self, update):
        templ_sites = Template(filename=self.input)
        text = templ_sites.render(**self.options)
        config = Configuration(self.buildout, self.name + '.conf', {
            'deployment': self.deployment_name,
            'directory': os.path.join(self.options['etc-directory'], 'conf.d'),
            'text': text})
        return [config.install()]

    def update(self):
        return self.install(update=True)

    def upgrade(self):
        pass


def uninstall(name, options):
    pass
