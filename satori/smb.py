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

"""Windows remote client module implemented using psexec.py."""

try:
    import eventlet
    eventlet.monkey_patch()
    from eventlet.green import time
except ImportError:
    import time

import ast
import base64
import logging
import os
import re
import shlex
import subprocess
import tempfile

from satori import ssh
from satori import tunnel

LOG = logging.getLogger(__name__)


def connect(*args, **kwargs):
    """Connect to a remote device using psexec.py."""
    try:
        return SMBClient.get_client(*args, **kwargs)
    except Exception as exc:
        LOG.error("ERROR: pse.py failed to connect: %s", str(exc))


def _posh_encode(command):
    """Encode a powershell command to base64.

    This is using utf-16 encoding and disregarding the first two bytes
    :param  command:    command to encode
    """
    return base64.b64encode(command.encode('utf-16')[2:])


class SubprocessError(Exception):

    """Custom Exception.

    This will be raised when the subprocess running psexec.py has exited.
    """

    pass


class SMBClient(object):  # pylint: disable=R0902

    """Connects to devices over SMB/psexec to execute commands."""

    _prompt_pattern = re.compile(r'^[a-zA-Z]:\\.*>$', re.MULTILINE)

    # pylint: disable=R0913
    def __init__(self, host, password=None, username="Administrator",
                 port=445, timeout=10, gateway=None, **kwargs):
        """Create an instance of the PSE class.

        :param str host:        The ip address or host name of the server
                                to connect to
        :param str password:    A password to use for authentication
        :param str username:    The username to authenticate as (defaults to
                                Administrator)
        :param int port:        tcp/ip port to use (defaults to 445)
        :param float timeout:   an optional timeout (in seconds) for the
                                TCP connection
        :param gateway:         instance of satori.ssh.SSH to be used to set up
                                an SSH tunnel (equivalent to ssh -L)
        """
        self.password = password
        self.host = host
        self.port = port or 445
        self.username = username or 'Administrator'
        self.timeout = timeout
        self._connected = False
        self._platform_info = None
        self._process = None
        self._orig_host = None
        self._orig_port = None
        self.ssh_tunnel = None
        self._substituted_command = None

        # creating temp file to talk to _process with
        self._file_write = tempfile.NamedTemporaryFile()
        self._file_read = open(self._file_write.name, 'r')

        self._command = ("nice python %s/contrib/psexec.py -port %s %s:%s@%s "
                         "'c:\\Windows\\sysnative\\cmd'")
        self._output = ''
        self.gateway = gateway

        if gateway:
            if not isinstance(self.gateway, ssh.SSH):
                raise TypeError("'gateway' must be a satori.ssh.SSH instance. "
                                "( instances of this type are returned by"
                                "satori.ssh.connect() )")

        if kwargs:
            LOG.debug("DEBUG: Following arguments passed into PSE constructor "
                      "not used: %s", kwargs.keys())

    def __del__(self):
        """Destructor of the PSE class."""
        try:
            self.close()
        except ValueError:
            pass

    @classmethod
    def get_client(cls, *args, **kwargs):
        """Return a pse client object from this module."""
        return cls(*args, **kwargs)

    @property
    def platform_info(self):
        """Return Windows edition, version and architecture.

        requires Powershell version 3
        """
        if not self._platform_info:
            command = ('Get-WmiObject Win32_OperatingSystem |'
                       ' select @{n="dist";e={$_.Caption.Trim()}},'
                       '@{n="version";e={$_.Version}},@{n="arch";'
                       'e={$_.OSArchitecture}} | '
                       ' ConvertTo-Json -Compress')
            stdout = self.remote_execute(command, retry=3)
            self._platform_info = ast.literal_eval(stdout)

        return self._platform_info

    def create_tunnel(self):
        """Create an ssh tunnel via gateway.

        This will tunnel a local ephemeral port to the host's port.
        This will preserve the original host and port
        """
        self.ssh_tunnel = tunnel.Tunnel(self.host, self.port, self.gateway)
        self._orig_host = self.host
        self._orig_port = self.port
        self.host, self.port = self.ssh_tunnel.address
        self.ssh_tunnel.serve_forever(async=True)

    def shutdown_tunnel(self):
        """Terminate the ssh tunnel. Restores original host and port."""
        self.ssh_tunnel.shutdown()
        self.host = self._orig_host
        self.port = self._orig_port

    def test_connection(self):
        """Connect to a Windows server and disconnect again.

        Make sure the returncode is 0, otherwise return False
        """
        self.connect()
        self.close()
        self._get_output()
        if self._output.find('ErrorCode: 0, ReturnCode: 0') > -1:
            return True
        else:
            return False

    def connect(self):
        """Attempt a connection using psexec.py.

        This will create a subprocess.Popen() instance and communicate with it
        via _file_read/_file_write and _process.stdin
        """
        try:
            if self._connected and self._process:
                if self._process.poll() is None:
                    return
                else:
                    self._process.wait()
                    if self.gateway:
                        self.shutdown_tunnel()
            if self.gateway:
                self.create_tunnel()
            self._substituted_command = self._command % (
                os.path.dirname(__file__),
                self.port,
                self.username,
                self.password,
                self.host)
            self._process = subprocess.Popen(
                shlex.split(self._substituted_command),
                stdout=self._file_write,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                close_fds=True,
                bufsize=0)
            output = ''
            while not self._prompt_pattern.findall(output):
                output += self._get_output()
            self._connected = True
        except Exception:
            self.close()
            raise

    def close(self):
        """Close the psexec connection by sending 'exit' to the subprocess.

        This will cleanly exit psexec (i.e. stop and uninstall the service and
        delete the files)

        This method will be called when an instance of this class is about to
        being destroyed. It will try to close the connection (which will clean
        up on the remote server) and catch the exception that is raised when
        the connection has already been closed.
        """
        try:
            self._process.communicate('exit')
        except Exception as exc:
            LOG.warning("ERROR: Failed to close %s: %s", self, str(exc))
            del exc
        try:
            if self.gateway:
                self.shutdown_tunnel()
                self.gateway.close()
        except Exception as exc:
            LOG.warning("ERROR: Failed to close gateway %s: %s", self.gateway,
                        str(exc))
            del exc
        finally:
            if self._process:
                LOG.warning("Killing process: %s", self._process)
                subprocess.call(['pkill', '-STOP', '-P',
                                str(self._process.pid)])

    def remote_execute(self, command, powershell=True, retry=0, **kwargs):
        """Execute a command on a remote host.

        :param command:     Command to be executed
        :param powershell:  If True, command will be interpreted as Powershell
                            command and therefore converted to base64 and
                            prepended with 'powershell -EncodedCommand
        :param int retry:   Number of retries when SubprocessError is thrown
                            by _get_output before giving up
        """
        self.connect()
        if powershell:
            command = ('powershell -EncodedCommand %s' %
                       _posh_encode(command))
        self._process.stdin.write('%s\n' % command)
        try:
            output = self._get_output()
            output = "\n".join(output.splitlines()[:-1]).strip()
            return output
        except SubprocessError:
            if not retry:
                raise
            else:
                return self.remote_execute(command, powershell=powershell,
                                           retry=retry - 1)

    def _get_output(self, prompt_expected=True, wait=200):
        """Retrieve output from _process.

        This method will wait until output is started to be received and then
        wait until no further output is received within a defined period
        :param prompt_expected:     only return when regular expression defined
                                    in _prompt_pattern is matched
        :param wait:                Time in milliseconds to wait in each of the
                                    two loops that wait for (more) output.
        """
        tmp_out = ''
        while tmp_out == '':
            self._file_read.seek(0, 1)
            tmp_out += self._file_read.read()
            # leave loop if underlying process has a return code
            # obviously meaning that it has terminated
            if self._process.poll() is not None:
                import json
                error = {"error": tmp_out}
                raise SubprocessError("subprocess with pid: %s has terminated "
                                      "unexpectedly with return code: %s\n%s"
                                      % (self._process.pid,
                                         self._process.poll(),
                                         json.dumps(error)))
            time.sleep(wait / 1000)
        stdout = tmp_out
        while (not tmp_out == '' or
               (not self._prompt_pattern.findall(stdout) and
                prompt_expected)):
            self._file_read.seek(0, 1)
            tmp_out = self._file_read.read()
            stdout += tmp_out
            # leave loop if underlying process has a return code
            # obviously meaning that it has terminated
            if self._process.poll() is not None:
                import json
                error = {"error": stdout}
                raise SubprocessError("subprocess with pid: %s has terminated "
                                      "unexpectedly with return code: %s\n%s"
                                      % (self._process.pid,
                                         self._process.poll(),
                                         json.dumps(error)))
            time.sleep(wait / 1000)
        self._output += stdout
        stdout = stdout.replace('\r', '').replace('\x08', '')
        return stdout
