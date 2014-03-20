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
    @mock.patch.object(ohai_solo, 'install_remote')
    def test_connect_and_run(self, mock_install, mock_sysinfo, mock_ssh):
        address = "123.345.678.0"
        config = mock.MagicMock()
        config.host_key = "foo"
        config.host_username = "bar"
        mock_sysinfo.return_value = {}
        result = ohai_solo.get_systeminfo(address, config)
        self.assertTrue(result is mock_sysinfo.return_value)

        mock_install.assert_called_once_with(mock_ssh.connect.return_value)
        mock_ssh.connect.assert_called_with(address, username="bar",
                                            private_key="foo",
                                            interactive=False)
        mock_sysinfo.assert_called_with(mock_ssh.connect.return_value)


class TestOhaiInstall(utils.TestCase):

    def test_install_remote_fedora(self):
        mock_ssh = mock.MagicMock()
        response = {'exit_code': 0, 'foo': 'bar'}
        mock_ssh.remote_execute.return_value = response
        result = ohai_solo.install_remote(mock_ssh)
        self.assertEqual(result, response)
        self.assertEqual(mock_ssh.remote_execute.call_count, 3)
        mock_ssh.remote_execute.assert_has_calls([
            mock.call("cd /tmp && sudo wget -N http://ohai.rax.io/install.sh"),
            mock.call("cd /tmp && bash install.sh", with_exit_code=True),
            mock.call("cd /tmp && rm install.sh")]
        )

    def test_install_remote_failed(self):
        mock_ssh = mock.MagicMock()
        response = {'exit_code': 1, 'stdout': "", "stderr": "FAIL"}
        mock_ssh.remote_execute.return_value = response
        self.assertRaises(errors.SystemInfoCommandInstallFailed,
                          ohai_solo.install_remote, mock_ssh)


class TestOhaiRemove(utils.TestCase):

    def test_remove_remote_fedora(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.platform_info = {
            'dist': 'centos',
            'version': "4",
            'arch': 'xyz'
        }
        response = {'exit_code': 0, 'foo': 'bar'}
        mock_ssh.remote_execute.return_value = response
        result = ohai_solo.remove_remote(mock_ssh)
        self.assertEqual(result, response)
        mock_ssh.remote_execute.assert_called_once_with(
            "cd /tmp && sudo yum -y erase ohai-solo")

    def test_remove_remote_debian(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.platform_info = {
            'dist': 'ubuntu',
            'version': "4",
            'arch': 'xyz'
        }
        response = {'exit_code': 0, 'foo': 'bar'}
        mock_ssh.remote_execute.return_value = response
        result = ohai_solo.remove_remote(mock_ssh)
        self.assertEqual(result, response)
        mock_ssh.remote_execute.assert_called_once_with(
            "cd /tmp && sudo dpkg --purge ohai-solo")

    def test_remove_remote_unsupported(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.platform_info = {'dist': 'amiga'}
        self.assertRaises(errors.UnsupportedPlatform,
                          ohai_solo.remove_remote, mock_ssh)


class TestSystemInfo(utils.TestCase):

    def test_system_info(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.remote_execute.return_value = {
            'exit_code': 0,
            'stdout': "{}",
            'stderr': ""
        }
        ohai_solo.system_info(mock_ssh)
        mock_ssh.remote_execute.assert_called_with("sudo -i ohai-solo")

    def test_system_info_with_motd(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.remote_execute.return_value = {
            'exit_code': 0,
            'stdout': "Hello world\n {}",
            'stderr': ""
        }
        ohai_solo.system_info(mock_ssh)
        mock_ssh.remote_execute.assert_called_with("sudo -i ohai-solo")

    def test_system_info_bad_json(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.remote_execute.return_value = {
            'exit_code': 0,
            'stdout': "{Not JSON!}",
            'stderr': ""
        }
        self.assertRaises(errors.SystemInfoNotJson, ohai_solo.system_info,
                          mock_ssh)

    def test_system_info_missing_json(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.remote_execute.return_value = {
            'exit_code': 0,
            'stdout': "No JSON!",
            'stderr': ""
        }
        self.assertRaises(errors.SystemInfoMissingJson, ohai_solo.system_info,
                          mock_ssh)

    def test_system_info_command_not_found(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.remote_execute.return_value = {
            'exit_code': 1,
            'stdout': "",
            'stderr': "ohai-solo command not found"
        }
        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.system_info, mock_ssh)

    def test_system_info_could_not_find(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.remote_execute.return_value = {
            'exit_code': 1,
            'stdout': "",
            'stderr': "Could not find ohai-solo."
        }
        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.system_info, mock_ssh)


if __name__ == "__main__":
    unittest.main()
