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
"""PoSh-Ohai Data Plane Discovery Module."""

import json
import logging

import ipaddress as ipaddress_module
import six

from satori import bash
from satori import errors
from satori import utils

LOG = logging.getLogger(__name__)


def get_systeminfo(ipaddress, config, interactive=False):
    """Run data plane discovery using this module against a host.

    :param ipaddress: address to the host to discover.
    :param config: arguments and configuration suppplied to satori.
    :keyword interactive: whether to prompt the user for information.
    """
    if (ipaddress in utils.get_local_ips() or
            ipaddress_module.ip_address(six.text_type(ipaddress)).is_loopback):

        client = bash.LocalShell()
        client.host = "localhost"
        client.port = 0
        perform_install(client)
        return system_info(client)

    else:
        with bash.RemoteShell(
                ipaddress, username=config['host_username'],
                private_key=config['host_key'],
                interactive=interactive) as client:
            perform_install(client)
            return system_info(client)


def system_info(client, with_install=False):
    """Run Posh-Ohai on a remote system and gather the output.

    :param client: :class:`smb.SMB` instance
    :returns: dict -- system information from PoSh-Ohai
    :raises: SystemInfoCommandMissing, SystemInfoCommandOld, SystemInfoNotJson
             SystemInfoMissingJson

        SystemInfoCommandMissing if `posh-ohai` is not installed.
        SystemInfoCommandOld if `posh-ohai` is not the latest.
        SystemInfoNotJson if `posh-ohai` does not return valid JSON.
        SystemInfoMissingJson if `posh-ohai` does not return any JSON.
    """
    if with_install:
        perform_install(client)

    if client.is_windows():
        powershell_command = 'Get-ComputerConfiguration'
        output = client.execute(powershell_command)
        unicode_output = "%s" % output
        try:
            results = json.loads(unicode_output)
        except ValueError:
            try:
                clean_output = get_json(unicode_output)
                results = json.loads(clean_output)
            except ValueError as err:
                raise errors.SystemInfoNotJson(err)
        return results
    else:
        raise errors.PlatformNotSupported(
            "PoSh-Ohai is a Windows-only sytem info provider. "
            "Target platform was %s", client.platform_info['dist'])


def perform_install(client):
    """Install PoSh-Ohai on remote system."""
    LOG.info("Installing (or updating) PoSh-Ohai on device %s at %s:%d",
             client.host, client.host, client.port)

    # Check is it is a windows box, but fail safely to Linux
    is_windows = False
    try:
        is_windows = client.is_windows()
    except Exception:
        pass
    if is_windows:
        powershell_command = ('[scriptblock]::Create((New-Object -TypeName '
                              'System.Net.WebClient).DownloadString('
                              '"http://ohai.rax.io/deploy.ps1"))'
                              '.Invoke()')
        # check output to ensure that installation was successful
        # if not, raise SystemInfoCommandInstallFailed
        output = client.execute(powershell_command)
        return output
    else:
        raise errors.PlatformNotSupported(
            "PoSh-Ohai is a Windows-only sytem info provider. "
            "Target platform was %s", client.platform_info['dist'])


def remove_remote(client):
    """Remove PoSh-Ohai from specifc remote system.

    Currently supports:
        - ubuntu [10.x, 12.x]
        - debian [6.x, 7.x]
        - redhat [5.x, 6.x]
        - centos [5.x, 6.x]
    """
    if client.is_windows():
        powershell_command = ('Remove-Item -Path (Join-Path -Path '
                              '$($env:PSModulePath.Split(";") '
                              '| Where-Object { $_.StartsWith('
                              '$env:SystemRoot)}) -ChildPath '
                              '"PoSh-Ohai") -Recurse -Force -ErrorAction '
                              'SilentlyContinue')
        output = client.execute(powershell_command)
        return output
    else:
        raise errors.PlatformNotSupported(
            "PoSh-Ohai is a Windows-only sytem info provider. "
            "Target platform was %s", client.platform_info['dist'])


def get_json(data):
    """Find the JSON string in data and return a string.

    :param data: :string:
    :returns: string -- JSON string stripped of non-JSON data
    :raises: SystemInfoMissingJson

        SystemInfoMissingJson if no JSON is returned.
    """
    try:
        first = data.index('{')
        last = data.rindex('}')
        return data[first:last + 1]
    except ValueError as exc:
        context = {"ValueError": "%s" % exc}
        raise errors.SystemInfoMissingJson(context)
