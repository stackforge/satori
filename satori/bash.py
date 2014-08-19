#   Copyright 2012-2013 OpenStack Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

"""Shell classes for executing commands on a system.

Execute commands over ssh or using the python subprocess module.
"""

import logging
import shlex
import subprocess

from satori import errors
from satori import smb
from satori import ssh
from satori import utils

LOG = logging.getLogger(__name__)


class ShellMixin(object):

    """Handle platform detection and define execute command."""

    def execute(self, command, **kwargs):
        """Execute a (shell) command on the target.

        :param command:         Shell command to be executed
        :param with_exit_code:  Include the exit_code in the return body.
        :param cwd:              The child's current directory will be changed
                                to `cwd` before it is executed. Note that this
                                directory is not considered when searching the
                                executable, so you can't specify the program's
                                path relative to this argument
        :returns:               a dict with stdin, stdout, and
                                (optionally), the exit_code of the call

        See SSH.remote_execute(), SMB.remote_execute(), and
        LocalShell.execute() for client-specific keyword arguments.
        """
        pass

    @property
    def platform_info(self):
        """Provide distro, version, architecture."""
        pass

    def is_debian(self):
        """Indicate whether the system is Debian based.

        Uses the platform_info property.
        """
        if not self.platform_info['dist']:
            raise errors.UndeterminedPlatform(
                'Unable to determine whether the system is Debian based.')
        return self.platform_info['dist'].lower() in ['debian', 'ubuntu']

    def is_fedora(self):
        """Indicate whether the system in Fedora based.

        Uses the platform_info property.
        """
        if not self.platform_info['dist']:
            raise errors.UndeterminedPlatform(
                'Unable to determine whether the system is Fedora based.')
        return (self.platform_info['dist'].lower() in
                ['redhat', 'centos', 'fedora', 'el'])

    def is_osx(self):
        """Indicate whether the system is Apple OSX based.

        Uses the platform_info property.
        """
        if not self.platform_info['dist']:
            raise errors.UndeterminedPlatform(
                'Unable to determine whether the system is OS X based.')
        return (self.platform_info['dist'].lower() in
                ['darwin', 'macosx'])

    def is_windows(self):
        """Indicate whether the system is Windows based.

        Uses the platform_info property.
        """
        if hasattr(self, '_client'):
            if isinstance(self._client, smb.SMBClient):
                return True
        if not self.platform_info['dist']:
            raise errors.UndeterminedPlatform(
                'Unable to determine whether the system is Windows based.')

        return self.platform_info['dist'].startswith('win')


class LocalShell(ShellMixin):

    """Execute shell commands on local machine."""

    def __init__(self, user=None, password=None, interactive=False):
        """An interface for executing shell commands locally.

        :param user:        The user to execute the command as.
                            Defaults to the current user.
        :param password:    The password for `user`
        :param interactive: If true, prompt for password if missing.

        """
        self.user = user
        self.password = password
        self.interactive = interactive

        # properties
        self._platform_info = None

    @property
    def platform_info(self):
        """Return distro, version, and system architecture."""
        if not self._platform_info:
            self._platform_info = utils.get_platform_info()
        return self._platform_info

    def execute(self, command, **kwargs):
        """Execute a command (containing no shell operators) locally.

        :param command:         Shell command to be executed.
        :param with_exit_code:  Include the exit_code in the return body.
                                Default is False.
        :param cwd:              The child's current directory will be changed
                                to `cwd` before it is executed. Note that this
                                directory is not considered when searching the
                                executable, so you can't specify the program's
                                path relative to this argument
        :returns:               A dict with stdin, stdout, and
                                (optionally) the exit code.
        """
        cwd = kwargs.get('cwd')
        with_exit_code = kwargs.get('with_exit_code')
        spipe = subprocess.PIPE

        cmd = shlex.split(command)
        LOG.debug("Executing `%s` on local machine", command)
        result = subprocess.Popen(
            cmd, stdout=spipe, stderr=spipe, cwd=cwd)
        out, err = result.communicate()
        resultdict = {
            'stdout': out.strip(),
            'stderr': err.strip(),
        }
        if with_exit_code:
            resultdict.update({'exit_code': result.returncode})
        return resultdict


class RemoteShell(ShellMixin):

    """Execute shell commands on a remote machine over ssh."""

    def __init__(self, address, password=None, username=None,
                 private_key=None, key_filename=None, port=None,
                 timeout=None, gateway=None, options=None, interactive=False,
                 protocol='ssh', **kwargs):
        """An interface for executing shell commands on remote machines.

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
        :param socket gateway:  an existing SSH instance to use
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
        if kwargs:
            LOG.warning("Satori RemoteClient received unrecognized "
                        "keyword arguments: %s", kwargs.keys())

        if protocol == 'smb':
            self._client = smb.connect(address, password=password,
                                       username=username,
                                       port=port, timeout=timeout,
                                       gateway=gateway)
        else:
            self._client = ssh.connect(address, password=password,
                                       username=username,
                                       private_key=private_key,
                                       key_filename=key_filename,
                                       port=port, timeout=timeout,
                                       gateway=gateway,
                                       options=options,
                                       interactive=interactive)
        self.host = self._client.host
        self.port = self._client.port

    @property
    def platform_info(self):
        """Return distro, version, architecture."""
        return self._client.platform_info

    def __del__(self):
        """Destructor which should close the connection."""
        self.close()

    def __enter__(self):
        """Context manager establish connection."""
        self.connect()
        return self

    def __exit__(self, *exc_info):
        """Context manager close connection."""
        self.close()

    def connect(self):
        """Connect to the remote host."""
        return self._client.connect()

    def test_connection(self):
        """Test the connection to the remote host."""
        return self._client.test_connection()

    def execute(self, command, **kwargs):
        """Execute given command over ssh."""
        return self._client.remote_execute(command, **kwargs)

    def close(self):
        """Close the connection to the remote host."""
        return self._client.close()
