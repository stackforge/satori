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
        result = templating.parse(self.template, data={})
        self.assertEqual(result.strip('\n'), 'Host not found')

    def test_target_is_ip(self):
        """Handles response when host is just the supplied address."""
        result = templating.parse(self.template, target='127.0.0.1',
                                  data={'address': '127.0.0.1'})
        self.assertEqual(result.strip('\n'),
                         'Host:\n    ip-address: 127.0.0.1')

    def test_host_not_server(self):
        """Handles response when host is not a nova instance."""
        result = templating.parse(self.template, target='localhost',
                                  data={'address': '127.0.0.1'})
        self.assertEqual(result.strip('\n'),
                         'Address:\n    localhost resolves to IPv4 address '
                         '127.0.0.1\nHost:\n    ip-address: 127.0.0.1')

    def test_host_is_nova_instance(self):
        """Handles response when host is a nova instance."""
        data = {
            'address': '10.1.1.45',
            'host': {
                'type': 'Nova instance',
                'uri': 'https://servers/path',
                'id': '1000B',
                'name': 'x',
                'addresses': {
                    'public': [{'type': 'ipv4', 'addr': '10.1.1.45'}]
                }
            }
        }
        result = templating.parse(self.template,
                                  target='instance.nova.local',
                                  data=data)
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
            10.1.1.45"""
        self.assertEqual(result.strip('\n'), expected)


if __name__ == '__main__':
    unittest.main()
