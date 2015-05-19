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
"""Test PoSh-Ohai Plugin."""

import unittest
import doctest

import mock

from satori import errors
from satori.sysinfo import posh_ohai
from satori.tests import utils


def load_tests(loader, tests, ignore):
    """Include doctests as unit tests."""
    tests.addTests(doctest.DocTestSuite(posh_ohai))
    return tests


class TestSystemInfo(utils.TestCase):

    def setUp(self):
        super(TestSystemInfo, self).setUp()
        self.client = mock.MagicMock()
        self.client.is_windows.return_value = True

    def test_system_info(self):
        self.client.execute.return_value = "{}"
        posh_ohai.system_info(self.client)
        self.client.execute.assert_called_with("Get-ComputerConfiguration")

    def test_system_info_json(self):
        self.client.execute.return_value = '{"foo": 123}'
        self.assertEqual(posh_ohai.system_info(self.client), {'foo': 123})

    def test_system_info_json_with_motd(self):
        self.client.execute.return_value = "Hello world\n {}"
        self.assertEqual(posh_ohai.system_info(self.client), {})

    def test_system_info_xml(self):
        valid_xml = '''<Objects>"
                         <Object>"
                           <Property Name="Key">platform_family</Property>
                           <Property Name="Value">Windows</Property>
                         </Object>
                       </Objects>'''
        self.client.execute.return_value = valid_xml
        self.assertEqual(posh_ohai.system_info(self.client),
                         {'platform_family': 'Windows'})

    def test_system_info_bad_json(self):
        self.client.execute.return_value = "{Not JSON!}"
        self.assertRaises(errors.SystemInfoInvalid,
                          posh_ohai.system_info, self.client)

    def test_system_info_bad_xml(self):
        self.client.execute.return_value = "<foo><bar>"
        self.assertRaises(errors.SystemInfoInvalid,
                          posh_ohai.system_info, self.client)

    def test_system_info_bad_xml(self):
        self.client.execute.return_value = "<foo>bad structure</foo>"
        self.assertRaises(errors.SystemInfoInvalid,
                          posh_ohai.system_info, self.client)

    def test_system_info_invalid(self):
        self.client.execute.return_value = "No JSON and not XML!"
        self.assertRaises(errors.SystemInfoInvalid,
                          posh_ohai.system_info, self.client)


if __name__ == "__main__":
    unittest.main()
