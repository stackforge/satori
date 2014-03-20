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
"""Ohai Solo Data Plane Discovery Module."""

import json
import logging

import six

from satori import errors
from satori import ssh

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
    ssh_client = ssh.connect(ipaddress, username=config.host_username,
                             private_key=config.host_key,
                             interactive=interactive)
    install_remote(ssh_client)
    return system_info(ssh_client)


def system_info(ssh_client):
    """Run ohai-solo on a remote system and gather the output.

    :param ssh_client: :class:`ssh.SSH` instance
    :returns: dict -- system information from ohai-solo
    :raises: SystemInfoCommandMissing, SystemInfoCommandOld, SystemInfoNotJson
             SystemInfoMissingJson

        SystemInfoCommandMissing if `ohai` is not installed.
        SystemInfoCommandOld if `ohai` is not the latest.
        SystemInfoNotJson if `ohai` does not return valid JSON.
        SystemInfoMissingJson if `ohai` does not return any JSON.
    """
    output = ssh_client.remote_execute("sudo -i ohai-solo")
    not_found_msgs = ["command not found", "Could not find ohai"]
    if any(m in k for m in not_found_msgs
           for k in list(output.values()) if isinstance(k, six.string_types)):
        LOG.warning("SystemInfoCommandMissing on host: [%s]", ssh_client.host)
        raise errors.SystemInfoCommandMissing("ohai-solo missing on %s",
                                              ssh_client.host)
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


def install_remote(ssh_client):
    """Install ohai-solo on remote system."""
    LOG.info("Installing (or updating) ohai-solo on device %s at %s:%d",
             ssh_client.host, ssh_client.host, ssh_client.port)
    # Download to host
    command = "cd /tmp && sudo wget -N http://ohai.rax.io/install.sh"
    ssh_client.remote_execute(command)

    # Run install
    command = "cd /tmp && bash install.sh"
    output = ssh_client.remote_execute(command, with_exit_code=True)

    # Be a good citizen and clean up your tmp data
    command = "cd /tmp && rm install.sh"
    ssh_client.remote_execute(command)

    # Process install command output
    if output['exit_code'] != 0:
        raise errors.SystemInfoCommandInstallFailed(output['stderr'][:256])
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
    platform_info = ssh_client.platform_info
    if is_debian(platform_info):
        remove = "sudo dpkg --purge ohai-solo"
    elif is_fedora(platform_info):
        remove = "sudo yum -y erase ohai-solo"
    else:
        raise errors.UnsupportedPlatform("Unknown distro: %s" %
                                         platform_info['dist'])
    command = "cd /tmp && %s" % remove
    output = ssh_client.remote_execute(command)
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
    except ValueError as e:
        context = {"ValueError": "%s" % e}
        raise errors.SystemInfoMissingJson(context)
