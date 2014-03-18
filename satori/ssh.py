#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""SSH Module for connecting to and automating remote commands.

Supports proxying, as in `ssh -A`

To control the behavior of the SSH client, use the specific connect_with_*
calls. The .connect() call behaves like the ssh command and attempts a number
of connection methods, including using the curent user's ssh keys.

If interactive is set to true, the module will also prompt for a password if no
other connection methods succeeded.

Note that test_connection() calls connect(). To test a connection and control
the authentication methods used, just call connect_with_* and catch any
exceptions instead of using test_connect().
"""

import ast
import getpass
import logging
import os
import re
import tempfile
import time

import paramiko
import six

from satori import errors

LOG = logging.getLogger(__name__)
MIN_PASSWORD_PROMPT_LEN = 8
MAX_PASSWORD_PROMPT_LEN = 64
TEMPFILE_PREFIX = ".satori.tmp.key."
TTY_REQUIRED = [
    "you must have a tty to run sudo",
    "is not a tty",
    "no tty present",
]


def make_pkey(private_key):
    """Return a paramiko.pkey.PKey from private key string."""
    key_classes = [paramiko.rsakey.RSAKey,
                   paramiko.dsskey.DSSKey,
                   paramiko.ecdsakey.ECDSAKey, ]

    keyfile = six.StringIO(private_key)
    for cls in key_classes:
        keyfile.seek(0)
        try:
            pkey = cls.from_private_key(keyfile)
        except paramiko.SSHException:
            continue
        else:
            keytype = cls
            LOG.info("Valid SSH Key provided (%s)", keytype.__name__)
            return pkey

    raise paramiko.SSHException("Is not a valid private key")


def connect(*args, **kwargs):
    """Connect to a remote device over SSH."""
    try:
        return SSH.get_client(*args, **kwargs)
    except TypeError as exc:
        msg = "got an unexpected"
        if msg in str(exc):
            message = "%s " + str(exc)[str(exc).index(msg):]
            raise exc.__class__(message % "connect()")
        raise


class AcceptMissingHostKey(paramiko.client.MissingHostKeyPolicy):

    """Allow connections to hosts whose fingerprints are not on record."""

    # pylint: disable=R0903
    def missing_host_key(self, client, hostname, key):
        """Add missing host key."""
        # pylint: disable=W0212
        client._host_keys.add(hostname, key.get_name(), key)


class SSH(paramiko.SSHClient):  # pylint: disable=R0902

    """Connects to devices via SSH to execute commands."""

    # pylint: disable=R0913
    def __init__(self, host, password=None, username="root",
                 private_key=None, key_filename=None, port=22,
                 timeout=20, proxy=None, options=None, interactive=False):
        """Create an instance of the SSH class.

        :param str host:        The ip address or host name of the server
                                to connect to
        :param str password:    A password to use for authentication
                                or for unlocking a private key
        :param username:        The username to authenticate as
        :param private_key:     Private SSH Key string to use
                                (instead of using a filename)
        :param key_filename:    a private key filename (path)
        :param port:            tcp/ip port to use (defaults to 22)
        :param float timeout:   an optional timeout (in seconds) for the
                                TCP connection
        :param socket proxy:    an existing SSH instance to use
                                for proxying
        :param dict options:    A dictionary used to set ssh options
                                (when proxying).
                                e.g. for `ssh -o StrictHostKeyChecking=no`,
                                you would provide
                                (.., options={'StrictHostKeyChecking': 'no'})
                                Conversion of booleans is also supported,
                                (.., options={'StrictHostKeyChecking': False})
                                is equivalent.
        :keyword interactive:   If true, prompt for password if missing.
        """
        self.password = password
        self.host = host
        self.username = username
        self.private_key = private_key
        self.key_filename = key_filename
        self.port = port
        self.timeout = timeout
        self._platform_info = None
        self.options = options or {}
        self.proxy = proxy
        self.sock = None
        self.interactive = interactive

        if self.proxy:
            if not isinstance(self.proxy, SSH):
                raise TypeError("'proxy' must be a satori.ssh.SSH instance. "
                                "( instances of this type are returned by "
                                "satori.ssh.connect() )")

        super(SSH, self).__init__()

    @classmethod
    def get_client(cls, *args, **kwargs):
        """Return an ssh client object from this module."""
        return cls(*args, **kwargs)

    @property
    def platform_info(self):
        """Return distro, version, architecture."""
        if not self._platform_info:
            command = ('python -c '
                       '"""import sys,platform as p;'
                       'plat=list(p.dist()+(p.machine(),));'
                       'sys.stdout.write(str(plat))"""')

            output = self.remote_execute(command)
            stdout = re.split('\n|\r\n', output['stdout'])[-1].strip()
            plat = ast.literal_eval(stdout)
            self._platform_info = {'dist': plat[0].lower(), 'version': plat[1],
                                   'arch': plat[3]}

        LOG.debug("Remote platform info: %s", self._platform_info)
        return self._platform_info

    def connect_with_host_keys(self):
        """Try connecting with locally available keys (ex. ~/.ssh/id_rsa)."""
        LOG.debug("Trying to connect with local host keys")
        return self._connect(look_for_keys=True, allow_agent=False)

    def connect_with_password(self):
        """Try connecting with password."""
        LOG.debug("Trying to connect with password")
        if self.interactive and not self.password:
            LOG.debug("Prompting for password (interactive=%s)",
                      self.interactive)
            try:
                self.password = getpass.getpass("Enter password for %s:" %
                                                self.username)
            except KeyboardInterrupt:
                LOG.debug("User cancelled at password prompt")
        if not self.password:
            raise paramiko.PasswordRequiredException("Password not provided")
        return self._connect(
            password=self.password,
            look_for_keys=False,
            allow_agent=False)

    def connect_with_key_file(self):
        """Try connecting with key file."""
        LOG.debug("Trying to connect with key file")
        if not self.key_filename:
            raise paramiko.AuthenticationException("No key file supplied")
        return self._connect(
            key_filename=os.path.expanduser(self.key_filename),
            look_for_keys=False,
            allow_agent=False)

    def connect_with_key(self):
        """Try connecting with key string."""
        LOG.debug("Trying to connect with private key string")
        if not self.private_key:
            raise paramiko.AuthenticationException("No key supplied")
        pkey = make_pkey(self.private_key)
        return self._connect(
            pkey=pkey,
            look_for_keys=False,
            allow_agent=False)

    def _connect(self, **kwargs):
        """Set up client and connect to target."""
        self.load_system_host_keys()

        if self.proxy:
            # lazy load
            self.sock = self._get_proxy_socket(self.proxy)

        if self.options.get('StrictHostKeyChecking') in (False, "no"):
            self.set_missing_host_key_policy(AcceptMissingHostKey())

        return super(SSH, self).connect(
            self.host,
            timeout=kwargs.pop('timeout', self.timeout),
            port=kwargs.pop('port', self.port),
            username=kwargs.pop('username', self.username),
            pkey=kwargs.pop('pkey', None),
            sock=kwargs.pop('sock', self.sock),
            **kwargs)

    def connect(self):  # pylint: disable=W0221
        """Attempt an SSH connection through paramiko.SSHClient.connect.

        The order for authentication attempts is:
        - private_key
        - key_filename
        - any key discoverable in ~/.ssh/
        - username/password (will prompt if the password is not supplied and
                             interactive is true)
        """
        if self.private_key:
            try:
                return self.connect_with_key()
            except paramiko.SSHException:
                pass  # try next method

        if self.key_filename:
            try:
                return self.connect_with_key_file()
            except paramiko.SSHException:
                pass  # try next method

        try:
            return self.connect_with_host_keys()
        except paramiko.SSHException:
            pass  # try next method

        try:
            return self.connect_with_password()
        except paramiko.BadHostKeyException as exc:
            msg = (
                "ssh://%s@%s:%d failed:  %s. You might have a bad key "
                "entry on your server, but this is a security issue and "
                "won't be handled automatically. To fix this you can remove "
                "the host entry for this host from the /.ssh/known_hosts file")
            LOG.info(msg, self.username, self.host, self.port, exc)
            raise exc
        except Exception as exc:
            LOG.info('ssh://%s@%s:%d failed.  %s',
                     self.username, self.host, self.port, exc)
            raise exc

    def test_connection(self):
        """Connect to an ssh server and verify that it responds.

        The order for authentication attempts is:
        (1) private_key
        (2) key_filename
        (3) any key discoverable in ~/.ssh/
        (4) username/password
        """
        LOG.debug("Checking for a response from ssh://%s@%s:%d.",
                  self.username, self.host, self.port)
        try:
            self.connect()
            LOG.debug("ssh://%s@%s:%d is up.",
                      self.username, self.host, self.port)
            return True
        except Exception as exc:
            LOG.info("ssh://%s@%s:%d failed.  %s",
                     self.username, self.host, self.port, exc)
            return False
        finally:
            self.close()

    def _handle_tty_required(self, results, get_pty):
        """Determine whether the result implies a tty request."""
        if any(m in str(k) for m in TTY_REQUIRED for k in results.values()):
            LOG.info('%s requires TTY for sudo. Using TTY mode.',
                     self.host)
            if get_pty is True:  # if this is *already* True
                raise errors.GetPTYRetryFailure(
                    "Running command with get_pty=True FAILED: %s@%s:%d"
                    % (self.username, self.host, self.port))
            else:
                return True
        return False

    def _handle_password_prompt(self, stdin, stdout):
        """Determine whether the remote host is prompting for a password.

        Respond to the prompt through stdin if applicable.
        """
        if not stdout.channel.closed:
            buflen = len(stdout.channel.in_buffer)
            # min and max determined from max username length
            # and a set of encountered linux password prompts
            if MIN_PASSWORD_PROMPT_LEN < buflen < MAX_PASSWORD_PROMPT_LEN:
                prompt = stdout.channel.recv(buflen)
                if all(m in prompt.lower()
                        for m in ['password', ':']):
                    LOG.warning("%s@%s encountered prompt! of length "
                                " [%s] {%s}",
                                self.username, self.host, buflen, prompt)
                    stdin.write("%s\n" % self.password)
                    stdin.flush()
                    return True
                else:
                    LOG.warning("Nearly a False-Positive on "
                                "password prompt detection. [%s] {%s}",
                                buflen, prompt)
                    stdout.channel.send(prompt)

        return False

    def remote_execute(self, command, with_exit_code=False,
                       get_pty=False, wd=None):
        """Execute an ssh command on a remote host.

        Tries cert auth first and falls back
        to password auth if password provided.

        :param command:         Shell command to be executed by this function.
        :param with_exit_code:  Include the exit_code in the return body.
        :param wd:              The child's current directory will be changed
                                to `wd` before it is executed. Note that this
                                directory is not considered when searching the
                                executable, so you can't specify the program's
                                path relative to this argument
        :param get_pty:         Request a pseudo-terminal from the server.

        :returns: a dict with stdin, stdout,
                  and (optionally) the exit code of the call.
        """
        if wd:
            prefix = "cd %s && " % wd
            command = prefix + command

        LOG.debug("Executing '%s' on ssh://%s@%s:%s.",
                  command, self.username, self.host, self.port)
        try:
            self.connect()

            results = None
            chan = self.get_transport().open_session()
            if get_pty:
                chan.get_pty()
            stdin = chan.makefile('wb')
            stdout = chan.makefile('rb')
            stderr = chan.makefile_stderr('rb')
            chan.exec_command(command)
            LOG.debug('ssh://%s@%s:%d responded.', self.username, self.host,
                      self.port)

            time.sleep(.25)
            self._handle_password_prompt(stdin, stdout)

            results = {
                'stdout': stdout.read().strip(),
                'stderr': stderr.read()
            }

            LOG.debug("STDOUT from ssh://%s@%s:%d: %s",
                      self.username, self.host, self.port,
                      results['stdout'])
            LOG.debug("STDERR from ssh://%s@%s:%d: %s",
                      self.username, self.host, self.port,
                      results['stderr'])
            exit_code = chan.recv_exit_status()

            if with_exit_code:
                results.update({'exit_code': exit_code})
            chan.close()

            if self._handle_tty_required(results, get_pty):
                return self.remote_execute(
                    command, with_exit_code=with_exit_code, get_pty=True)

            return results

        except Exception as exc:
            LOG.info("ssh://%s@%s:%d failed.  %s", self.username, self.host,
                     self.port, exc)
            raise
        finally:
            self.close()

    def _get_proxy_socket(self, proxy):
        """Return a wrapped subprocess running ProxyCommand-driven programs.

        Create a new CommandProxy instance.
        Can be created from an existing SSH instance.
        For proxy clients, please specify a private key filename.

        To use an ssh proxy, you must use an SSH Key,
        since a ProxyCommand cannot be passed a password.
        """
        if proxy.password:
            LOG.warning("Proxying through a client which is authorized by "
                        "a password is not currently implemented. Please "
                        "use an ssh key.")

        proxy.load_system_host_keys()
        if proxy.options.get('StrictHostKeyChecking') in (False, "no"):
            proxy.set_missing_host_key_policy(AcceptMissingHostKey())

        if proxy.private_key and not proxy.key_filename:
            tempkeyfile = tempfile.NamedTemporaryFile(
                mode='w+', prefix=TEMPFILE_PREFIX,
                dir=os.path.expanduser('~/'), delete=True)
            tempkeyfile.write(proxy.private_key)
            proxy.key_filename = tempkeyfile.name

        pxd = {
            'bastion': proxy.host,
            'user': proxy.username,
            'port': '-p %s' % proxy.port,
            'options': ('-o ConnectTimeout=%s ' % proxy.timeout),
            'target_host': self.host,
            'target_port': self.port,
        }
        proxycommand = "ssh {options} -A {user}@{bastion} "

        if proxy.key_filename:
            proxy.key_filename = os.path.expanduser(proxy.key_filename)
            proxy.key_filename = os.path.abspath(proxy.key_filename)
            pxd.update({'identity': '-i %s' % proxy.key_filename})
            proxycommand += "{identity} "

        if proxy.options:
            for key, val in sorted(proxy.options.items()):
                if isinstance(val, bool):
                    # turns booleans into `ssh -o` compat "yes" or "no"
                    if val is True:
                        val = "yes"
                    if val is False:
                        val = "no"
                pxd['options'] += '-o %s=%s ' % (key, val)

        proxycommand += "nc {target_host} {target_port}"
        return paramiko.ProxyCommand(proxycommand.format(**pxd))

# Share SSH.__init__'s docstring
connect.__doc__ = SSH.__init__.__doc__
try:
    SSH.__dict__['get_client'].__doc__ = SSH.__dict__['__init__'].__doc__
except AttributeError:
    SSH.get_client.__func__.__doc__ = SSH.__init__.__doc__
