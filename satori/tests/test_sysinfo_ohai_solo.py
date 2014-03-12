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
"""Test Ohai-Solo Plugin."""

import unittest

import mock

from satori import errors
from satori.sysinfo import ohai_solo
from satori.tests import utils


class TestOhaiSolo(utils.TestCase):

    @mock.patch.object(ohai_solo, 'ssh')
    @mock.patch.object(ohai_solo, 'system_info')
    def test_connect_and_run(self, mock_sysinfo, mock_ssh):
        address = "123.345.678.0"
        config = mock.MagicMock()
        config.host_key = "foo"
        mock_sysinfo.return_value = {}
        result = ohai_solo.get_systeminfo(address, config)
        self.assertTrue(result is mock_sysinfo.return_value)

        mock_ssh.connect.assert_called_with(host=address, private_key="foo")
        mock_sysinfo.assert_called_with(mock_ssh.connect.return_value)

    @mock.patch.object(ohai_solo, 'ssh')
    @mock.patch.object(ohai_solo, 'system_info')
    @mock.patch.object(ohai_solo, 'install_remote')
    def test_install_if_missing(self, mock_install, mock_sysinfo, mock_ssh):
        config = mock.MagicMock()
        mock_sysinfo.side_effect = errors.SystemInfoCommandMissing(None)

        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.get_systeminfo, "localhost", config)

        mock_install.assert_called_once_with(mock_ssh.connect.return_value)
        self.assertEqual(mock_sysinfo.call_count, 2)
        mock_sysinfo.calls[0][0] is mock_ssh.connect.return_value
        # re-runs after install
        mock_sysinfo.calls[1][0] is mock_ssh.connect.return_value

    @mock.patch.object(ohai_solo, 'ssh')
    @mock.patch.object(ohai_solo, 'system_info')
    @mock.patch.object(ohai_solo, 'install_remote')
    @mock.patch.object(ohai_solo, 'remove_remote')
    def test_reinstall_if_old(self, mock_remove, mock_install, mock_sysinfo,
                              mock_ssh):
        config = mock.MagicMock()
        mock_sysinfo.side_effect = errors.SystemInfoCommandOld(None)

        self.assertRaises(errors.SystemInfoCommandOld,
                          ohai_solo.get_systeminfo, "localhost", config)

        mock_remove.assert_called_once_with(mock_ssh.connect.return_value)
        mock_install.assert_called_once_with(mock_ssh.connect.return_value)
        self.assertEqual(mock_sysinfo.call_count, 2)
        mock_sysinfo.calls[0][0] is mock_ssh.connect.return_value
        # re-runs after install
        mock_sysinfo.calls[1][0] is mock_ssh.connect.return_value

    @mock.patch.object(ohai_solo, 'ssh')
    @mock.patch.object(ohai_solo, 'system_info')
    def test_raise_others(self, mock_sysinfo, mock_ssh):
        config = mock.MagicMock()
        mock_sysinfo.side_effect = errors.DiscoveryException(None)

        self.assertRaises(errors.DiscoveryException,
                          ohai_solo.get_systeminfo, "locahost", config)



if __name__ == "__main__":
    unittest.main()
