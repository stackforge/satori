"""Returns an sshclient OR a localhost client with a consistent interface."""

import logging
import platform
import shlex
import socket
import subprocess

from satori import ssh

LOG = logging.getLogger(__name__)


def platform_info():
    "Return distro, version, and system architecture."""

    return list(platform.dist() + (platform.machine(),))


def local_ips():
    """Return local ipaddress(es)."""

    localnames = ['localhost', '127.0.0.1']
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        localnames.append(sock.getsockname()[0])
    except socket.error:
        pass
    finally:
        sock.close()

    localnames.append(socket.gethostbyname(socket.gethostname()))
    localnames.append(socket.gethostbyname(socket.getfqdn()))
    localnames = list(set(localnames))
    return localnames


def local_execute(self, command, wd=None, with_exit_code=True):
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

