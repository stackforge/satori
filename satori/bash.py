"""Shell classes for executing commands on a system.

Execute commands over ssh or using python subprocess module.
"""

import logging
import platform
import shlex
import subprocess

from satori import ssh

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
        pass

    def is_debian(self):
        return self.platform['dist'].lower() in ['debian', 'ubuntu']

    def is_fedora(self):
        return (self.platform['dist'].lower() in
            ['redhat', 'centos', 'fedora', 'el'])

class LocalShell(ShellMixin):

    def __init__(self, user=None, password=None, interactive=False):

        self.user = user
        self.password = password
        self.interactive = interactive
        # TODO(samstav): Implement handle_password_prompt for popen

    @property
    def platform_info(self):
        "Return distro, version, and system architecture."""

        return list(platform.dist() + (platform.machine(),))


    def execute(self, command, wd=None, with_exit_code=None):
        """Execute a command (containing no shell operators) locally."""
        spipe = subprocess.PIPE

        cmd = shlex.split(command)
        LOG.debug("Executing `%s` on local machine", command)
        result = subprocess.Popen(
            cmd, stdout=spipe, stderr=spipe, cwd=wd)
        out, err = result.communicate()
        resultdict = {'stdout': out.strip(),
                      'stderr': err.strip(),
        }
        if with_exit_code:
            resultdict.update({'exit_code': result.returncode})
        return resultdict


class RemoteShell(ShellMixin):

    def __init__(self, address, **kwargs):
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
