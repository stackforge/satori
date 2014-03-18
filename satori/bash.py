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
from satori import ssh
from satori import utils

LOG = logging.getLogger(__name__)


class ShellMixin(object):

    """Handle platform detection and define execute command."""

    def execute(self, command, wd=None, with_exit_code=None):
        """Execute a (shell) command on the target.

        :param command:         Shell command to be executed
        :param with_exit_code:  Include the exit_code in the return body.
        :param wd:              The child's current directory will be changed
                                to `wd` before it is executed. Note that this
                                directory is not considered when searching the
                                executable, so you can't specify the program's
                                path relative to this argument
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

        Uses the platform info property.
        """
        if not self.platform_info['dist']:
            raise errors.UndeterminedPlatform(
                'Unable to determine whether the system is Fedora based.')
        return (self.platform_info['dist'].lower() in
                ['redhat', 'centos', 'fedora', 'el'])

    def is_osx(self):
        """Indicate whether the system is Apple OSX based."""
        if not self.platform_info['dist']:
            raise errors.UndeterminedPlatform(
                'Unable to determine whether the system is OS X based.')
        return (self.platform_info['dist'].lower() in
                ['darwin', 'macosx'])

    def is_windows(self):
        """Indicate whether the system is Windows based."""
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
        # TODO(samstav): Implement handle_password_prompt for popen

        # properties
        self._platform_info = None

    @property
    def platform_info(self):
        """Return distro, version, and system architecture."""
        if not self._platform_info:
            self._platform_info = utils.get_platform_info()
        return self._platform_info

    def execute(self, command, wd=None, with_exit_code=None):
        """Execute a command (containing no shell operators) locally.

        :param command:         Shell command to be executed.
        :param with_exit_code:  Include the exit_code in the return body.
                                Default is False.
        :param wd:              The child's current directory will be changed
                                to `wd` before it is executed. Note that this
                                directory is not considered when searching the
                                executable, so you can't specify the program's
                                path relative to this argument
        :returns:               A dict with stdin, stdout, and
                                (optionally) the exit code.
        """
        spipe = subprocess.PIPE

        cmd = shlex.split(command)
        LOG.debug("Executing `%s` on local machine", command)
        result = subprocess.Popen(
            cmd, stdout=spipe, stderr=spipe, cwd=wd)
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

    def __init__(self, address, **kwargs):
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
        self.sshclient = ssh.connect(address, **kwargs)
        self.host = self.sshclient.host
        self.port = self.sshclient.port

    @property
    def platform_info(self):
        """Return distro, version, architecture."""
        return self.sshclient.platform_info

    def execute(self, command, wd=None, with_exit_code=None):
        """Execute given command over ssh."""
        return self.sshclient.remote_execute(
            command, wd=wd, with_exit_code=with_exit_code)
