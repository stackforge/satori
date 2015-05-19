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
import xml.etree.ElementTree as ET

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
    :raises: SystemInfoCommandMissing, SystemInfoCommandOld, SystemInfoInvalid
             SystemInfoMissingJson, SystemInfoInvalidXml

        SystemInfoCommandMissing if `posh-ohai` is not installed.
        SystemInfoCommandOld if `posh-ohai` is not the latest.
        SystemInfoInvalid if `posh-ohai` does not return valid JSON or XML.
        SystemInfoMissingJson if `posh-ohai` does not return any JSON.
        SystemInfoInvalidXml if `posh-ohai` returned unexpected XML.
    """
    if with_install:
        perform_install(client)

    if client.is_windows():
        powershell_command = 'Get-ComputerConfiguration'
        output = client.execute(powershell_command)
        unicode_output = "%s" % output
        load_clean_json = lambda output: json.loads(get_json(output))
        last_err = None
        for loader in json.loads, parse_xml, load_clean_json:
            try:
                return loader(unicode_output)
            except ValueError as err:
                last_err = err
        raise errors.SystemInfoInvalid(last_err)
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
                              '"http://readonly.configdiscovery.rackspace.com'
                              '/deploy.ps1")).Invoke()')
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


def parse_text(elem):
    """Parse text from an element.

    >>> parse_text(ET.XML('<Property>Hello World</Property>'))
    'Hello World'
    >>> parse_text(ET.XML('<Property>True  </Property>'))
    True
    >>> parse_text(ET.XML('<Property>123</Property>'))
    123
    >>> print parse_text(ET.XML('<Property />'))
    None
    """
    if elem.text is None:
        return None
    try:
        return int(elem.text)
    except ValueError:
        pass
    text = elem.text.strip()
    if text == 'True':
        return True
    if text == 'False':
        return False
    return elem.text


def parse_list(elem):
    """Parse list of properties.

    >>> parse_list(ET.XML('<Property />'))
    []
    >>> xml = '''<Property>
    ...            <Property>Hello</Property>
    ...            <Property>World</Property>
    ...          </Property>'''
    >>> parse_list(ET.XML(xml))
    ['Hello', 'World']
    """
    return map(parse_elem, elem)


def parse_attrib_dict(elem):
    """Parse list of properties.

    >>> parse_attrib_dict(ET.XML('<Property />'))
    {}
    >>> xml = '''<Property>
    ...            <Property Name="verb">Hello</Property>
    ...            <Property Name="noun">World</Property>
    ...          </Property>'''
    >>> d = parse_attrib_dict(ET.XML(xml))
    >>> sorted(d.items())
    [('noun', 'World'), ('verb', 'Hello')]
    """
    keys = [c.get('Name') for c in elem]
    values = [parse_elem(c) for c in elem]
    return dict(zip(keys, values))


def parse_key_value_dict(elem):
    """Parse list of properties.

    >>> parse_key_value_dict(ET.XML('<Property />'))
    {}
    >>> xml = '''<Property>
    ...            <Property Name="Key">verb</Property>
    ...            <Property Name="Value">Hello</Property>
    ...            <Property Name="Key">noun</Property>
    ...            <Property Name="Value">World</Property>
    ...          </Property>'''
    >>> d = parse_key_value_dict(ET.XML(xml))
    >>> sorted(d.items())
    [('noun', 'World'), ('verb', 'Hello')]
    """
    keys = [c.text for c in elem[::2]]
    values = [parse_elem(c) for c in elem[1::2]]
    return dict(zip(keys, values))


def parse_elem(elem):
    """Determine element type and dispatch to other parse functions."""
    if len(elem) == 0:
        return parse_text(elem)
    if not elem[0].attrib:
        return parse_list(elem)
    if elem[0].get('Name') == 'Key':
        return parse_key_value_dict(elem)
    return parse_attrib_dict(elem)


def parse_xml(ohai_output):
    r"""Parse XML Posh-Ohai output.

    >>> output = '''\
    ... <?xml version="1.0"?>
    ... <Objects>
    ...   <Object>
    ...     <Property Name="Key">platform_family</Property>
    ...     <Property Name="Value">Windows</Property>
    ...     <Property Name="Key">logonhistory</Property>
    ...     <Property Name="Value">
    ...       <Property Name="Key">0x6dd0359</Property>
    ...       <Property Name="Value">
    ...         <Property Name="Key">user</Property>
    ...         <Property Name="Value">WIN2008R2\\Administrator</Property>
    ...         <Property Name="Key">logontype</Property>
    ...         <Property Name="Value">10</Property>
    ...       </Property>
    ...     </Property>
    ...     <Property Name="Key">loggedon_users</Property>
    ...     <Property Name="Value">
    ...       <Property>
    ...         <Property Name="Session">995</Property>
    ...         <Property Name="User">WIN2008R2\IUSR</Property>
    ...         <Property Name="Type">Service</Property>
    ...       </Property>
    ...       <Property>
    ...         <Property Name="Session">999</Property>
    ...         <Property Name="User">WIN2008R2\SYSTEM</Property>
    ...         <Property Name="Type">Local System</Property>
    ...       </Property>
    ...     </Property>
    ...   </Object>
    ... </Objects>'''
    >>> import pprint
    >>> pprint.pprint(parse_xml(output))
    {'loggedon_users': [{'Session': 995,
                         'Type': 'Service',
                         'User': 'WIN2008R2\\IUSR'},
                        {'Session': 999,
                         'Type': 'Local System',
                         'User': 'WIN2008R2\\SYSTEM'}],
     'logonhistory': {'0x6dd0359': {'logontype': 10,
                                    'user': 'WIN2008R2\\Administrator'}},
     'platform_family': 'Windows'}
    """
    try:
        root = ET.XML(ohai_output)
    except ET.ParseError as err:
        raise ValueError(err)
    try:
        properties = root[0]
    except IndexError as err:
        raise errors.SystemInfoInvalidXml(err)
    return parse_elem(properties)
