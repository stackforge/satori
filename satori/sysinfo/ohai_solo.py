"""Ohai Solo Data Plane Discovery Module."""

import json
import logging

import requests

from satori import errors
from satori import ssh

LOG = logging.getLogger(__name__)
OHAI_SOLO_URL_TEMPLATE = "http://ohai.rax.io/%s"


def get_systeminfo(ipaddress, config):
    """Run data plane discovery using this module against a host."""
    ssh_client = ssh.connect(host=ipaddress, private_key=config.host_key)
    try:
        result = system_info(ssh_client)
    except errors.SystemInfoCommandMissing as exc:
        LOG.exception(exc)
        install_remote(ssh_client)
        return system_info(ssh_client)
    except errors.SystemInfoCommandOld as exc:
        LOG.exception(exc)
        remove_remote(ssh_client)
        install_remote(ssh_client)
        return system_info(ssh_client)
    except errors.DiscoveryException as exc:
        LOG.exception(exc)
        LOG.error("Error running ohai-solo: %s", exc)
        raise

    return result


def system_info(ssh_client):
    """Run ohai-solo on a remote system and gathers the output.

    :param ssh_client: ssh.SSH instance
    :return type: dict
    :returns: system information from `ohai`
    Raises:
        SystemInfoCommandMissing if `ohai` is not installed.
        SystemInfoCommandOld if `ohai` is not the latest.
        SystemInfoNotJson if `ohai` does not return valid json.
    """

    # first check version
    current_version = get_remote_version(ssh_client)
    if not is_remote_latest(ssh_client, current_version):
        raise errors.SystemInfoCommandOld("Old version: %s" % current_version)

    output = ssh_client.remote_execute("sudo -i ohai-solo")

    LOG.debug("STDOUT from ssh://%s@%s:%d: %s",
              ssh_client.username, ssh_client.host, ssh_client.port,
              output['stdout'])
    LOG.debug("STDERR from ssh://%s@%s:%d: %s",
              ssh_client.username, ssh_client.host, ssh_client.port,
              output['stderr'])

    not_found_msgs = ["command not found", "Could not find ohai"]
    if any(m in k for m in not_found_msgs for k in output.values()):
        LOG.warning("SystemInfoCommandMissing on host: [%s]", ssh_client.host)
        raise errors.SystemInfoCommandMissing("ohai-solo missing on %s",
                                              ssh_client.host)

    try:
        results = json.loads(unicode(output['stdout'], errors='replace'))
    except ValueError as exc:
        raise errors.SystemInfoNotJson(exc)

    current_version = results['ohai_solo']['version']

    if not is_remote_latest(ssh_client, current_version):
        raise errors.SystemInfoCommandOld(
            "Old version: %s" % current_version)

    return results


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
    ohai_url_spec = OHAI_SOLO_URL_TEMPLATE % pkg_spec
    ohai_url = ohai_url_spec.format(**plat)
    LOG.debug("Getting ohai package info from url: %s", ohai_url)
    headers = {'Content-Type': 'application/json'}
    response = requests.get(ohai_url, headers=headers, verify=False)
    try:
        loaded = response.json()
    except ValueError as exc:
        LOG.error("Failed to decode.", exc_info=exc)
        raise
    return loaded


def get_remote_version(ssh_client):
    """Read /opt/ohai-solo/version-manifest.txt.

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


def install_remote(ssh_client):
    """Install ohai-solo on a specifc remote system.

    Currently supports:
        - ubuntu [10.x, 12.x]
        - debian [6.x, 7.x]
        - redhat [5.x, 6.x]
        - centos [5.x, 6.x]
    """
    LOG.info("(Re)installing ohai-solo on device %s at %s:%d",
             ssh_client.host, ssh_client.host, ssh_client.port)
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
        raise errors.SystemInfoCommandInstallFailed(context)
    else:
        return output


def remove_remote(ssh_client):
    """Remove ohai-solo from specifc remote system.

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


def is_remote_latest(ssh_client, current_version):
    """Return true if the installed ohai-solo package is the latest."""
    pkg_info = get_upstream_ohai_solo_pkg_info(ssh_client)
    latest_version = pkg_info['version']
    if not str(current_version) == latest_version:
        return False
    return True


if __name__ == "__main__":
    from satori.tests import test_sysinfo_ohai_solo as tests
    tests.unittest.main(tests)
