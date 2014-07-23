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

"""Discovery Module.

    TODO(zns): testing, refactoring, etc...  just using this to demonstrate
    functionality

Example usage:

    from satori import discovery
    discovery.run(address="foo.com")
"""

from __future__ import print_function

import sys
import traceback

import ipaddress
from novaclient.v1_1 import client
from pythonwhois import shared
import six

from satori import dns
from satori import utils


def run(target, config=None, interactive=False):
    """Run discovery and return results."""
    if config is None:
        config = {}

    found = {}
    resources = {}
    errors = {}
    results = {
        'target': target,
        'created': utils.get_time_string(),
        'found': found,
        'resources': resources,
    }
    if utils.is_valid_ip_address(target):
        ip_address = target
    else:
        hostname = dns.parse_target_hostname(target)
        found['hostname'] = hostname
        ip_address = six.text_type(dns.resolve_hostname(hostname))
        # TODO(sam): Use ipaddress.ip_address.is_global
        #                                    .is_private
        #                                    .is_unspecified
        #                                    .is_multicast
        #       To determine address "type"
        if not ipaddress.ip_address(ip_address).is_loopback:
            try:
                domain_info = dns.domain_info(hostname)
                resource_type = 'OS::DNS::Domain'
                identifier = '%s:%s' % (resource_type, hostname)
                resources[identifier] = {
                    'type': resource_type,
                    'key': identifier,
                }
                found['domain-key'] = identifier
                resources[identifier]['data'] = domain_info
                if 'registered' in domain_info:
                    found['registered-domain'] = domain_info['registered']
            except shared.WhoisException as exc:
                results['domain'] = str(exc)
    found['ip-address'] = ip_address

    host, host_errors = discover_host(ip_address, config,
                                      interactive=interactive)
    if host_errors:
        errors.update(host_errors)
    key = host.get('key') or ip_address
    resources[key] = host
    found['host-key'] = key
    results['updated'] = utils.get_time_string()
    return results, errors


def discover_host(address, config, interactive=False):
    """Discover host by IP address."""
    host = {}
    errors = {}
    if config.get('username'):
        server = find_nova_host(address, config)
        if server:
            host['type'] = 'OS::Nova::Instance'
            data = {}
            host['data'] = data
            data['uri'] = [l['href'] for l in server.links
                           if l['rel'] == 'self'][0]
            data['name'] = server.name
            data['id'] = server.id
            data['addresses'] = server.addresses
            host['key'] = data['uri']

    if config.get('system_info'):
        module_name = config['system_info'].replace("-", "_")
        if '.' not in module_name:
            module_name = 'satori.sysinfo.%s' % module_name
        system_info_module = utils.import_object(module_name)
        try:
            result = system_info_module.get_systeminfo(
                address, config, interactive=interactive)
            host.setdefault('data', {})
            host['data']['system_info'] = result
        except Exception as exc:
            exc_traceback = sys.exc_info()[2]
            errors['system_info'] = {
                'type': "ERROR",
                'message': str(exc),
                'exception': exc,
                'traceback': traceback.format_tb(exc_traceback),
            }
    return host, errors


def find_nova_host(address, config):
    """See if a nova instance has the supplied address."""
    nova = client.Client(config['username'],
                         config['password'],
                         config['tenant_id'],
                         config['authurl'],
                         region_name=config['region'],
                         service_type="compute")
    for server in nova.servers.list():
        for network_addresses in six.itervalues(server.addresses):
            for ip_address in network_addresses:
                if ip_address['addr'] == address:
                    return server
