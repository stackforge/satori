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

Supports proxying through an ssh tunnel ('gateway' keyword argument.)

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
import time

import paramiko
import six

from satori import errors
from satori import utils

LOG = logging.getLogger(__name__)
MIN_PASSWORD_PROMPT_LEN = 8
MAX_PASSWORD_PROMPT_LEN = 64
TEMPFILE_PREFIX = ".satori.tmp.key."
TTY_REQUIRED = [
    "you must have a tty to run sudo",
    "is not a tty",
    "no tty present",
    "must be run from a terminal",
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
    def __init__(self, host, password=None, username="root", private_key=None,
                 root_password=None, key_filename=None, port=22,
                 timeout=20, gateway=None, options=None, interactive=False):
        """Create an instance of the SSH class.

        :param str host:        The ip address or host name of the server
                                to connect to
        :param str password:    A password to use for authentication
                                or for unlocking a private key
        :param username:        The username to authenticate as
        :param root_password:   root user password to be used if 'username'
                                is not root. This will use 'username' and
                                'password to login and then 'su' to root
                                using root_password
        :param private_key:     Private SSH Key string to use
                                (instead of using a filename)
        :param key_filename:    a private key filename (path)
        :param port:            tcp/ip port to use (defaults to 22)
        :param float timeout:   an optional timeout (in seconds) for the
                                TCP connection
        :param socket gateway:    an existing SSH instance to use
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
        self.username = username or 'root'
        self.root_password = root_password
        self.private_key = private_key
        self.key_filename = key_filename
        self.port = port or 22
        self.timeout = timeout
        self._platform_info = None
        self.options = options or {}
        self.gateway = gateway
        self.sock = None
        self.interactive = interactive

        self.escalation_command = 'sudo -i %s'
        if self.root_password:
            self.escalation_command = "su -c '%s'"

        if self.gateway:
            if not isinstance(self.gateway, SSH):
                raise TypeError("'gateway' must be a satori.ssh.SSH instance. "
                                "( instances of this type are returned by "
                                "satori.ssh.connect() )")

        super(SSH, self).__init__()

    def __del__(self):
        """Destructor to close the connection."""
        self.close()

    @classmethod
    def get_client(cls, *args, **kwargs):
        """Return an ssh client object from this module."""
        return cls(*args, **kwargs)

    @property
    def platform_info(self):
        """Return distro, version, architecture.

        Requires >= Python 2.4 on remote system.
        """
        if not self._platform_info:
            platform_command = "import platform,sys\n"
            platform_command += utils.get_source_definition(
                utils.get_platform_info)
            platform_command += ("\nsys.stdout.write(str("
                                 "get_platform_info()))\n")
            command = 'echo -e """%s""" | python' % platform_command
            output = self.remote_execute(command)
            stdout = re.split('\n|\r\n', output['stdout'])[-1].strip()
            if stdout:
                try:
                    plat = ast.literal_eval(stdout)
                except SyntaxError as exc:
                    plat = {'dist': 'unknown'}
                    LOG.warning("Error parsing response from host '%s': %s",
                                self.host, output, exc_info=exc)
            else:
                plat = {'dist': 'unknown'}
                LOG.warning("Blank response from host '%s': %s",
                            self.host, output)
            self._platform_info = plat
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

        if self.options.get('StrictHostKeyChecking') in (False, "no"):
            self.set_missing_host_key_policy(AcceptMissingHostKey())

        if self.gateway:
            # lazy load
            if not self.gateway.get_transport():
                self.gateway.connect()
            self.sock = self.gateway.get_transport().open_channel(
                'direct-tcpip', (self.host, self.port), ('', 0))

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
        # idempotency
        if self.get_transport():
            if self.get_transport().is_active():
                return

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

    def close(self):
        """Close the connection to the remote host.

        If an ssh tunnel is being used, close that first.
        """
        if self.gateway:
            self.gateway.close()
        return super(SSH, self).close()

    def _handle_tty_required(self, results, get_pty):
        """Determine whether the result implies a tty request."""
        if any(m in str(k) for m in TTY_REQUIRED for k in results.values()):
            LOG.info('%s requires TTY for sudo/su. Using TTY mode.',
                     self.host)
            if get_pty is True:  # if this is *already* True
                raise errors.GetPTYRetryFailure(
                    "Running command with get_pty=True FAILED: %s@%s:%d"
                    % (self.username, self.host, self.port))
            else:
                return True
        return False

    def _handle_password_prompt(self, stdin, stdout, su_auth=False):
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
                    if su_auth:
                        LOG.warning("Escalating using 'su -'.")
                        stdin.write("%s\n" % self.root_password)
                    else:
                        stdin.write("%s\n" % self.password)
                    stdin.flush()
                    return True
                else:
                    LOG.warning("Nearly a False-Positive on "
                                "password prompt detection. [%s] {%s}",
                                buflen, prompt)
                    stdout.channel.send(prompt)

        return False

    def _command_is_already_running(self, command):
        """Check to see if the command is already running using ps & grep."""
        # check plain 'command' w/o prefix or escalation
        check_cmd = 'ps -ef |grep -v grep|grep -c "%s"' % command
        result = self.remote_execute(check_cmd, keepalive=True,
                                     allow_many=True)
        if result['stdout'] != '0':
            return True
        else:
            LOG.debug("Remote command %s IS NOT already running. "
                      "Continuing with remote_execute.", command)

    def remote_execute(self, command, with_exit_code=False,  # noqa
                       get_pty=False, cwd=None, keepalive=True,
                       escalate=False, allow_many=True, **kw):
        """Execute an ssh command on a remote host.

        Tries cert auth first and falls back
        to password auth if password provided.

        :param command:         Shell command to be executed by this function.
        :param with_exit_code:  Include the exit_code in the return body.
        :param cwd:             The child's current directory will be changed
                                to `cwd` before it is executed. Note that this
                                directory is not considered when searching the
                                executable, so you can't specify the program's
                                path relative to this argument
        :param get_pty:         Request a pseudo-terminal from the server.
        :param allow_many:      If False, do not run command if it is already
                                found running on remote client.

        :returns: a dict with stdin, stdout,
                  and (optionally) the exit code of the call.
        """
        if escalate and self.username != 'root':
            run_command = self.escalation_command % command
        else:
            run_command = command

        if cwd:
            prefix = "cd %s && " % cwd
            run_command = prefix + run_command

        # _command_is_already_running wont be called if allow_many is True
        # python is great :)
        if not allow_many and self._command_is_already_running(command):
            raise errors.SatoriDuplicateCommandException(
                "Remote command %s is already running and allow_many was "
                "set to False. Aborting remote_execute." % command)
        try:
            self.connect()
            results = None
            chan = self.get_transport().open_session()
            su_auth = False
            if 'su -' in run_command:
                su_auth = True
                get_pty = True
            if get_pty:
                chan.get_pty()
            stdin = chan.makefile('wb')
            stdout = chan.makefile('rb')
            stderr = chan.makefile_stderr('rb')
            LOG.debug("Executing '%s' on ssh://%s@%s:%s.",
                      run_command, self.username, self.host, self.port)
            chan.exec_command(run_command)
            LOG.debug('ssh://%s@%s:%d responded.', self.username, self.host,
                      self.port)

            time.sleep(.25)
            self._handle_password_prompt(stdin, stdout, su_auth=su_auth)

            results = {
                'stdout': stdout.read().strip(),
                'stderr': stderr.read()
            }

            LOG.debug("STDOUT from ssh://%s@%s:%d: %.5000s ...",
                      self.username, self.host, self.port,
                      results['stdout'])
            LOG.debug("STDERR from ssh://%s@%s:%d: %.5000s ...",
                      self.username, self.host, self.port,
                      results['stderr'])
            exit_code = chan.recv_exit_status()

            if with_exit_code:
                results.update({'exit_code': exit_code})
            if not keepalive:
                chan.close()

            if self._handle_tty_required(results, get_pty):
                return self.remote_execute(
                    command, with_exit_code=with_exit_code, get_pty=True,
                    cwd=cwd, keepalive=keepalive, escalate=escalate,
                    allow_many=allow_many)

            return results

        except Exception as exc:
            LOG.info("ssh://%s@%s:%d failed. | %s", self.username, self.host,
                     self.port, exc)
            raise
        finally:
            if not keepalive:
                self.close()


# Share SSH.__init__'s docstring
connect.__doc__ = SSH.__init__.__doc__
try:
    SSH.__dict__['get_client'].__doc__ = SSH.__dict__['__init__'].__doc__
except AttributeError:
    SSH.get_client.__func__.__doc__ = SSH.__init__.__doc__
