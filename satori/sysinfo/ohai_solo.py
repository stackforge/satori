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
# pylint: disable=W0622
"""Ohai Solo Data Plane Discovery Module."""

import json
import logging

import ipaddress as ipaddress_module
import six

from satori import bash
from satori import errors
from satori import utils

LOG = logging.getLogger(__name__)
if six.PY3:
    def unicode(text, errors=None):  # noqa
        """A hacky Python 3 version of unicode() function."""
        return str(text)


def get_systeminfo(ipaddress, config, interactive=False):
    """Run data plane discovery using this module against a host.

    :param ipaddress: address to the host to discover.
    :param config: arguments and configuration suppplied to satori.
    :keyword interactive: whether to prompt the user for information.
    """
    if (ipaddress in utils.get_local_ips() or
            ipaddress_module.ip_address(unicode(ipaddress)).is_loopback):

        client = bash.LocalShell()
        client.host = "localhost"
        client.port = 0

    else:
        client = bash.RemoteShell(ipaddress, username=config.host_username,
                                  private_key=config.host_key,
                                  interactive=interactive)

    install_remote(client)
    return system_info(client)


def system_info(client):
    """Run ohai-solo on a remote system and gather the output.

    :param client: :class:`ssh.SSH` instance
    :returns: dict -- system information from ohai-solo
    :raises: SystemInfoCommandMissing, SystemInfoCommandOld, SystemInfoNotJson
             SystemInfoMissingJson

        SystemInfoCommandMissing if `ohai` is not installed.
        SystemInfoCommandOld if `ohai` is not the latest.
        SystemInfoNotJson if `ohai` does not return valid JSON.
        SystemInfoMissingJson if `ohai` does not return any JSON.
    """
    output = client.execute("sudo -i ohai-solo")
    not_found_msgs = ["command not found", "Could not find ohai"]
    if any(m in k for m in not_found_msgs
           for k in list(output.values()) if isinstance(k, six.string_types)):
        LOG.warning("SystemInfoCommandMissing on host: [%s]", client.host)
        raise errors.SystemInfoCommandMissing("ohai-solo missing on %s",
                                              client.host)
    unicode_output = unicode(output['stdout'], errors='replace')
    try:
        results = json.loads(unicode_output)
    except ValueError as exc:
        try:
            clean_output = get_json(unicode_output)
            results = json.loads(clean_output)
        except ValueError as exc:
            raise errors.SystemInfoNotJson(exc)
    return results


def is_debian(platform):
    """Return true if the platform is a debian-based distro."""
    return platform['dist'].lower() in ['debian', 'ubuntu']


def is_fedora(platform):
    """Return true if the platform is a fedora-based distro."""
    return platform['dist'].lower() in ['redhat', 'centos', 'fedora', 'el']


def install_remote(client):
    """Install ohai-solo on remote system."""
    LOG.info("Installing (or updating) ohai-solo on device %s at %s:%d",
             client.host, client.host, client.port)
    # Download to host
    command = "sudo wget -N http://ohai.rax.io/install.sh"
    client.execute(command, wd='/tmp')

    # Run install
    command = "sudo bash install.sh"
    output = client.execute(command, wd='/tmp', with_exit_code=True)

    # Be a good citizen and clean up your tmp data
    command = "sudo rm install.sh"
    client.execute(command, wd='/tmp')

    # Process install command output
    if output['exit_code'] != 0:
        raise errors.SystemInfoCommandInstallFailed(output['stderr'][:256])
    else:
        return output


def remove_remote(client):
    """Remove ohai-solo from specifc remote system.

    Currently supports:
        - ubuntu [10.x, 12.x]
        - debian [6.x, 7.x]
        - redhat [5.x, 6.x]
        - centos [5.x, 6.x]
    """
    platform_info = client.platform_info
    if is_debian(platform_info):
        remove = "sudo dpkg --purge ohai-solo"
    elif is_fedora(platform_info):
        remove = "sudo yum -y erase ohai-solo"
    else:
        raise errors.UnsupportedPlatform("Unknown distro: %s" %
                                         platform_info['dist'])
    command = "%s" % remove
    output = client.execute(command, wd='/tmp')
    return output


def get_json(data):
    """Find the JSON string in data and return a string.

    :param data: :string:
    :returns: string -- JSON string striped of non-JSON data
    :raises: SystemInfoMissingJson

        SystemInfoMissingJson if `ohai` does not return any JSON.
    """
    try:
        first = data.index('{')
        last = data.rindex('}')
        return data[first:last + 1]
    except ValueError as exc:
        context = {"ValueError": "%s" % exc}
        raise errors.SystemInfoMissingJson(context)
