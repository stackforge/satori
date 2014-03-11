"""."""

import json
import logging

import requests

from satori import ssh

LOG = logging.getLogger(__name__)
OHAI_SOLO_URL_TEMPLATE = "http://ohai.rax.io/%s"


def get_systeminfo(ipaddress, config):
    """."""
    sshclient = ssh.connect(host=ipaddress,
                            private_key=config.host_key)
    result = system_info(sshclient)
    return {'ohai-solo': result}


class DiscoveryException(Exception):

    """Discovery exception with custom message."""


class SystemInfoCommandMissing(DiscoveryException):

    """Command that provides system information is missing."""


class SystemInfoCommandOld(DiscoveryException):

    """Command that provides system information is outdated."""


class SystemInfoNotJson(DiscoveryException):

    """Command did not produce valid JSON."""


class SystemInfoCommandInstallFailed(DiscoveryException):

    """Failed to install package that provides system information."""


def system_info(ssh_client):
    """Makes an SSH connection to `host` and gathers ohai output.

    Returns system information from `ohai` in json format. Raises
    SystemInfoCommandMissing exception if `ohai` is not installed.
    """

    # first check version
    current_version = get_ohai_solo_version(ssh_client)
    if not is_latest_ohai_solo(ssh_client, current_version):
        raise SystemInfoCommandOld("Old version: %s" % current_version)

    output = ssh_client.remote_execute("sudo -i ohai-solo")
    context = {'Platform': ssh_client.platform_info,
               'stdout': str(output['stdout'][:5000] + "...TRUNCATED"),
               'stderr': str(output['stderr'][:5000] + "...TRUNCATED")}
    LOG.debug("STDOUT from ssh://%s@%s:%d: %s",
              ssh_client.username, ssh_client.host, ssh_client.port,
              output['stdout'])
    LOG.debug("STDERR from ssh://%s@%s:%d: %s",
              ssh_client.username, ssh_client.host, ssh_client.port,
              output['stderr'])

    cnotfound = ["command not found", "Could not find ohai"]
    if any(m in k for m in cnotfound for k in output.values()):
        LOG.warning("SystemInfoCommandMissing on host: [%s] | "
                    "device_id: [%s]", ssh_client.host, ssh_client.device_id)
        raise SystemInfoCommandMissing(context)

    try:
        stdout = json.loads(unicode(output['stdout'], errors='replace'))
    except ValueError as exc:
        context.update({"ValueError": "%s" % exc})
        raise SystemInfoNotJson(context)

    current_version = stdout['ohai_solo']['version']

    if not is_latest_ohai_solo(ssh_client, current_version):
        raise SystemInfoCommandOld(
            "Old version: %s" % current_version)

    return stdout


def get_upstream_ohai_solo_pkg_info(ssh_client, which='latest'):
    """Determine package url."""
    plat = ssh_client.platform_info
    # build url according to gospel of st. walker
    if plat['dist'] in ['redhat', 'centos', 'el']:
        int_version = plat['version'].partition('.')[0]
        plat.update({'dist': 'el', 'version': int_version})

    elif plat['dist'] == 'debian':
        # 5, not 5.10; 6, not 6.0.7
        int_version = plat['version'].partition('.')[0]
        plat.update({'version': int_version})

    pkg_spec = "%s.{dist}.{version}.{arch}.json" % which
    ohai_url = OHAI_SOLO_URL_TEMPLATE % pkg_spec
    ohai_url = ohai_url.format(**plat)
    LOG.info("Getting ohai package info from url: %s", ohai_url)
    headers = {'Content-Type': 'application/json'}
    response = requests.get(ohai_url, headers=headers, verify=False)
    try:
        loaded = response.json()
    except ValueError as exc:
        LOG.error("Failed to decode.", exc_info=exc)
        raise
    return loaded


def get_ohai_solo_version(ssh_client):
    """Reads /opt/ohai-solo/version-manifest.txt.

    Should be fairly foolproof.
    """
    path = "/opt/ohai-solo/version-manifest.txt"
    command = "sudo cat %s" % path
    output = ssh_client.remote_execute(command, with_exit_code=True)
    if output['exit_code'] != 0:
        LOG.info('[ %s ] not found.', path)
        return
    else:
        info = ''
        cat = output['stdout'].splitlines()
        for line in cat:
            if "ohai-solo" in line:
                info = line.split()
                break

    for line in info:
        if len(line.split('.')) == 3:
            LOG.info("Determined ohai-solo version on system: %s", line)
            return line


def install_ohai_solo(ssh_client):
    """Installs ohai-solo for a specifc remote system.

    Currently supports:
        - ubuntu [10.x, 12.x]
        - debian [6.x, 7.x]
        - redhat [5.x, 6.x]
        - centos [5.x, 6.x]
    """
    LOG.info("(Re)installing ohai-solo on device %s at %s:%d",
             ssh_client.device_id, ssh_client.host, ssh_client.port)
    pkg_filename = get_upstream_ohai_solo_pkg_info(ssh_client)['basename']
    pkg_url = OHAI_SOLO_URL_TEMPLATE % pkg_filename
    LOG.debug("Package url: %s", pkg_url)
    command = "cd /tmp && sudo wget -N %s" % pkg_url
    ssh_client.remote_execute(command)

    if ssh_client.platform_info['dist'] in ['ubuntu', 'debian']:
        install = "sudo dpkg -i %s"
    elif ssh_client.platform_info['dist'] in ['redhat', 'centos', 'el']:
        install = "sudo yum --nogpgcheck -y install %s"

    command = "cd /tmp && " + install % pkg_filename

    output = ssh_client.remote_execute(command, with_exit_code=True)
    context = {'Platform': ssh_client.platform_info,
               'stdout': str(output['stdout'][:5000] + "...TRUNCATED"),
               'stderr': str(output['stderr'][:5000] + "...TRUNCATED")}
    if output['exit_code'] != 0:
        raise SystemInfoCommandInstallFailed(context)
    else:
        return output


def remove_ohai_solo(ssh_client):
    """Removes ohai-solo from specifc remote system.
    Currently supports:
        - ubuntu [10.x, 12.x]
        - debian [6.x, 7.x]
        - redhat [5.x, 6.x]
        - centos [5.x, 6.x]
    """

    if ssh_client.platform_info['dist'] in ['ubuntu', 'debian']:
        remove = "sudo dpkg --purge ohai-solo"
    elif ssh_client.platform_info['dist'] in ['redhat', 'centos', 'el']:
        remove = "sudo yum -y erase ohai-solo"

    command = "cd /tmp && " + remove
    output = ssh_client.remote_execute(command)
    return output


def is_latest_ohai_solo(ssh_client, current_version):
    """Returns true if the installed ohai-solo package is the latest."""
    pkg_info = get_upstream_ohai_solo_pkg_info(ssh_client)
    latest_version = pkg_info['version']
    if not str(current_version) == latest_version:
        return False
    return True
