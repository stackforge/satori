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
#
# pylint: disable=R0902, R0913
"""SSH Module for connecting to and automating remote commands.

Supports proxying, as in `ssh -A`
"""
import ast
import logging
import os
import re
import StringIO
import tempfile
import time

import paramiko

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


def connect(*args, **kwargs):
    """Connect to a remote device over SSH."""
    try:
        return SSH.get_client(*args, **kwargs)
    except TypeError as exc:
        msg = "got an unexpected"
        if msg in exc.message:
            message = "%s " + exc.message[exc.message.index(msg):]
            raise exc.__class__(message % "connect()")
        raise


class AcceptMissingHostKey(paramiko.client.MissingHostKeyPolicy):

    """Allow connections to hosts whose fingerprints are not on record."""

    # pylint: disable=R0903
    def missing_host_key(self, client, hostname, key):
        """Add missing host key."""
        # pylint: disable=W0212
        client._host_keys.add(hostname, key.get_name(), key)


class SSH(paramiko.SSHClient):

    """Connects to devices via SSH to execute commands."""

    def __init__(self, host, password=None, username="root",
                 private_key=None, key_filename=None, port=22,
                 timeout=20, proxy=None, options=None):
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
        if proxy:
            if not hasattr(proxy, 'host'):
                raise TypeError("Keyword 'proxy' requires a `host` attribute.")
            self.sock = self._get_proxy_socket(proxy)
        else:
            self.sock = None
        super(SSH, self).__init__()

    @staticmethod
    def _get_pkey(private_key):
        """Return a paramiko.pkey.PKey from private key string."""
        key_classes = [paramiko.rsakey.RSAKey,
                       paramiko.dsskey.DSSKey,
                       paramiko.ecdsakey.ECDSAKey, ]

        keyfile = StringIO.StringIO(private_key)
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

    def connect(self, use_password=False):  # pylint: disable=W0221
        """Attempt an SSH connection through paramiko.SSHClient.connect .

        The order for authentication attempts is:
        - private_key
        - key_filename
        - any key discoverable in ~/.ssh/
        - username/password

        :param use_password: Skip SSH keys when authenticating.
        """

        self.load_system_host_keys()

        if self.options.get('StrictHostKeyChecking') in (False, "no"):
            self.set_missing_host_key_policy(AcceptMissingHostKey())

        try:
            if self.private_key is not None and not use_password:
                pkey = self._get_pkey(self.private_key)
                LOG.debug("Trying supplied private key string")
                return super(SSH, self).connect(
                    self.host,
                    timeout=self.timeout,
                    port=self.port,
                    username=self.username,
                    pkey=pkey,
                    sock=self.sock)
            elif self.key_filename is not None and not use_password:
                LOG.debug("Trying key file: %s",
                          os.path.expanduser(self.key_filename))
                return super(SSH, self).connect(
                    self.host, timeout=self.timeout, port=self.port,
                    username=self.username,
                    key_filename=os.path.expanduser(self.key_filename),
                    sock=self.sock)
            else:
                return super(SSH, self).connect(
                    self.host, port=self.port,
                    username=self.username,
                    password=self.password,
                    sock=self.sock)
                LOG.debug("Authentication for ssh://%s@%s:%d using "
                          "password succeeded",
                          self.username, self.host, self.port)
            LOG.debug("Connected to ssh://%s@%s:%d.",
                      self.username, self.host, self.port)

        except paramiko.PasswordRequiredException as exc:
            #Looks like we have cert issues, so try password auth if we can
            if self.password and not use_password:  # dont recurse twice
                LOG.debug("Retrying with password credentials")
                return self.connect(use_password=True)
            else:
                raise exc
        except paramiko.BadHostKeyException as exc:
            msg = (
                "ssh://%s@%s:%d failed:  %s. You might have a bad key "
                "entry on your server, but this is a security issue and "
                "won't be handled automatically. To fix this you can remove "
                "the host entry for this host from the /.ssh/known_hosts file"
                % (self.username, self.host, self.port, exc))
            LOG.info(msg)
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
            if self.sock and not self.get_transport():
                self.connect()
            if not self.sock:
                self.connect()
            LOG.debug("ssh://%s@%s:%d is up.",
                      self.username, self.host, self.port)
            return True

        except Exception as exc:
            LOG.info("ssh://%s@%s:%d failed.  %s",
                     self.username, self.host, self.port, exc)
            return False
        finally:
            if not self.sock:
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

    def remote_execute(self, command, with_exit_code=False, get_pty=False):
        """Execute an ssh command on a remote host.

        Tries cert auth first and falls back
        to password auth if password provided.

        :param command:         Shell command to be executed by this function.
        :param with_exit_code:  Include the exit_code in the return body.
        :param get_pty:         Request a pseudo-terminal from the server.

        :returns: a dict with stdin, stdout,
                  and (optionally) the exit code of the call.
        """
        LOG.debug("Executing '%s' on ssh://%s@%s:%s.",
                  command, self.username, self.host, self.port)
        try:
            if self.sock and not self.get_transport():
                self.connect()
            if not self.sock:
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
            if not self.sock:
                self.close()

    def _get_proxy_socket(self, proxy):
        """Return a wrapped subprocess running ProxyCommand-driven programs.

        Create a new CommandProxy instance.
        Can be created from an existing SSH instance.
        For proxy clients, please specify a private key filename.

        To use an ssh proxy, you must use an SSH Key,
        since a ProxyCommand cannot be passed a password.
        """
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
            for key, val in proxy.options.items():
                if isinstance(val, bool):
                    # turns booleans into `ssh -o` compat "yes" or "no"
                    if val is True:
                        val = "yes"
                    if val is False:
                        val = "no"
                pxd['options'] += '%s=%s ' % (key, val)

        proxycommand += "nc {target_host} {target_port}"
        return paramiko.ProxyCommand(proxycommand.format(**pxd))

# Share SSH.__init__'s docstring
connect.__doc__ = SSH.__init__.__doc__
SSH.get_client.__func__.__doc__ = SSH.__init__.__func__.__doc__
