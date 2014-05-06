# pylint: disable=C0103,R0904

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

"""Tests for Format Templates."""

import unittest

from satori.common import templating
from satori import shell


class TestTextTemplate(unittest.TestCase):

    """Test Text Template."""

    def setUp(self):
        self.template = shell.get_template('text')

    def test_no_data(self):
        """Handles response with no host."""
        env_vars = dict(lstrip_blocks=True, trim_blocks=True)
        result = templating.parse(self.template, data={}, env_vars=env_vars)
        self.assertEqual(result.strip('\n'), 'Host not found')

    def test_target_is_ip(self):
        """Handles response when host is just the supplied address."""
        env_vars = dict(lstrip_blocks=True, trim_blocks=True)
        result = templating.parse(self.template, target='127.0.0.1',
                                  data={'found': {'ip-address': '127.0.0.1'}},
                                  env_vars=env_vars)
        self.assertEqual(result.strip('\n'),
                         'Host:\n    ip-address: 127.0.0.1')

    def test_host_not_server(self):
        """Handles response when host is not a nova instance."""
        env_vars = dict(lstrip_blocks=True, trim_blocks=True)
        result = templating.parse(self.template, target='localhost',
                                  data={'found': {'ip-address': '127.0.0.1'}},
                                  env_vars=env_vars)
        self.assertEqual(result.strip('\n'),
                         'Address:\n    localhost resolves to IPv4 address '
                         '127.0.0.1\nHost:\n    ip-address: 127.0.0.1')

    def test_host_is_nova_instance(self):
        """Handles response when host is a nova instance."""
        data = {
            'found': {
                'ip-address': '10.1.1.45',
                'hostname': 'x',
                'host-key': 'https://servers/path'
            },
            'target': 'instance.nova.local',
            'resources': {
                'https://servers/path': {
                    'type': 'OS::Nova::Instance',
                    'data': {
                        'uri': 'https://servers/path',
                        'id': '1000B',
                        'name': 'x',
                        'addresses': {
                            'public': [{'type': 'ipv4', 'addr': '10.1.1.45'}]
                        },
                        'system_info': {
                            'connections': {
                                '192.168.2.100': [],
                                '192.168.2.101': [433],
                                '192.168.2.102': [8080, 8081]
                            },
                            'remote_services': [
                                {
                                    'ip': '0.0.0.0',
                                    'process': 'nginx',
                                    'port': 80
                                }
                            ]
                        }
                    }
                }
            }
        }
        env_vars = dict(lstrip_blocks=True, trim_blocks=True)
        result = templating.parse(self.template,
                                  target='instance.nova.local',
                                  data=data, env_vars=env_vars)
        expected = """\
Address:
    instance.nova.local resolves to IPv4 address 10.1.1.45
Host:
    10.1.1.45 (instance.nova.local) is hosted on a Nova instance
    Instance Information:
        URI: https://servers/path
        Name: x
        ID: 1000B
    ip-addresses:
        public:
            10.1.1.45
    Listening Services:
        0.0.0.0:80  nginx
    Talking to:
        192.168.2.102 on 8080, 8081
        192.168.2.101 on 433
        192.168.2.100"""
        self.assertEqual(result.strip('\n'), expected)

    def test_host_has_no_data(self):
        """Handles response when host is a nova instance."""
        data = {
            'found': {
                'ip-address': '10.1.1.45',
                'hostname': 'x',
                'host-key': 'https://servers/path'
            },
            'target': 'instance.nova.local',
            'resources': {
                'https://servers/path': {
                    'type': 'OS::Nova::Instance'
                }
            }
        }
        env_vars = dict(lstrip_blocks=True, trim_blocks=True)
        result = templating.parse(self.template,
                                  target='instance.nova.local',
                                  data=data, env_vars=env_vars)
        expected = """\
Address:
    instance.nova.local resolves to IPv4 address 10.1.1.45
Host:
    10.1.1.45 (instance.nova.local) is hosted on a Nova instance"""
        self.assertEqual(result.strip('\n'), expected)

    def test_host_data_missing_items(self):
        """Handles response when host is a nova instance."""
        data = {
            'found': {
                'ip-address': '10.1.1.45',
                'hostname': 'x',
                'host-key': 'https://servers/path'
            },
            'target': 'instance.nova.local',
            'resources': {
                'https://servers/path': {
                    'type': 'OS::Nova::Instance',
                    'data': {
                        'id': '1000B',
                        'system_info': {
                            'remote_services': [
                                {
                                    'ip': '0.0.0.0',
                                    'process': 'nginx',
                                    'port': 80
                                }
                            ]
                        }
                    }
                }
            }
        }
        env_vars = dict(lstrip_blocks=True, trim_blocks=True)
        result = templating.parse(self.template,
                                  target='instance.nova.local',
                                  data=data, env_vars=env_vars)
        expected = """\
Address:
    instance.nova.local resolves to IPv4 address 10.1.1.45
Host:
    10.1.1.45 (instance.nova.local) is hosted on a Nova instance
    Instance Information:
        URI: n/a
        Name: n/a
        ID: 1000B
    Listening Services:
        0.0.0.0:80  nginx"""
        self.assertEqual(result.strip('\n'), expected)


if __name__ == '__main__':
    unittest.main()
