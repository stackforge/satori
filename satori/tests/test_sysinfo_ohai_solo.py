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

    @mock.patch.object(ohai_solo, 'bash')
    @mock.patch.object(ohai_solo, 'system_info')
    @mock.patch.object(ohai_solo, 'install_remote')
    def test_connect_and_run(self, mock_install, mock_sysinfo, mock_bash):
        address = "192.0.2.2"
        config = {
            'host_key': 'foo',
            'host_username': 'bar',
        }
        mock_sysinfo.return_value = {}
        result = ohai_solo.get_systeminfo(address, config)
        self.assertTrue(result is mock_sysinfo.return_value)

        mock_install.assert_called_once_with(
            mock_bash.RemoteShell.return_value)

        mock_bash.RemoteShell.assert_called_with(
            address, username="bar",
            private_key="foo",
            interactive=False)
        mock_sysinfo.assert_called_with(mock_bash.RemoteShell.return_value)


class TestOhaiInstall(utils.TestCase):

    def test_install_remote_fedora(self):
        mock_ssh = mock.MagicMock()
        response = {'exit_code': 0, 'foo': 'bar'}
        mock_ssh.execute.return_value = response
        result = ohai_solo.install_remote(mock_ssh)
        self.assertEqual(result, response)
        self.assertEqual(mock_ssh.execute.call_count, 3)
        mock_ssh.execute.assert_has_calls([
            mock.call('sudo wget -N http://ohai.rax.io/install.sh', wd='/tmp'),
            mock.call('sudo bash install.sh', wd='/tmp', with_exit_code=True),
            mock.call('sudo rm install.sh', wd='/tmp')])

    def test_install_remote_failed(self):
        mock_ssh = mock.MagicMock()
        response = {'exit_code': 1, 'stdout': "", "stderr": "FAIL"}
        mock_ssh.execute.return_value = response
        self.assertRaises(errors.SystemInfoCommandInstallFailed,
                          ohai_solo.install_remote, mock_ssh)


class TestOhaiRemove(utils.TestCase):

    def test_remove_remote_fedora(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.is_debian.return_value = False
        mock_ssh.is_fedora.return_value = True
        response = {'exit_code': 0, 'foo': 'bar'}
        mock_ssh.execute.return_value = response
        result = ohai_solo.remove_remote(mock_ssh)
        self.assertEqual(result, response)
        mock_ssh.execute.assert_called_once_with(
            'sudo yum -y erase ohai-solo', wd='/tmp')

    def test_remove_remote_debian(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.is_debian.return_value = True
        mock_ssh.is_fedora.return_value = False
        response = {'exit_code': 0, 'foo': 'bar'}
        mock_ssh.execute.return_value = response
        result = ohai_solo.remove_remote(mock_ssh)
        self.assertEqual(result, response)
        mock_ssh.execute.assert_called_once_with(
            'sudo dpkg --purge ohai-solo', wd='/tmp')

    def test_remove_remote_unsupported(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.is_debian.return_value = False
        mock_ssh.is_fedora.return_value = False
        self.assertRaises(errors.UnsupportedPlatform,
                          ohai_solo.remove_remote, mock_ssh)


class TestSystemInfo(utils.TestCase):

    def test_system_info(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.execute.return_value = {
            'exit_code': 0,
            'stdout': "{}",
            'stderr': ""
        }
        ohai_solo.system_info(mock_ssh)
        mock_ssh.execute.assert_called_with("sudo -i ohai-solo")

    def test_system_info_with_motd(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.execute.return_value = {
            'exit_code': 0,
            'stdout': "Hello world\n {}",
            'stderr': ""
        }
        ohai_solo.system_info(mock_ssh)
        mock_ssh.execute.assert_called_with("sudo -i ohai-solo")

    def test_system_info_bad_json(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.execute.return_value = {
            'exit_code': 0,
            'stdout': "{Not JSON!}",
            'stderr': ""
        }
        self.assertRaises(errors.SystemInfoNotJson, ohai_solo.system_info,
                          mock_ssh)

    def test_system_info_missing_json(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.execute.return_value = {
            'exit_code': 0,
            'stdout': "No JSON!",
            'stderr': ""
        }
        self.assertRaises(errors.SystemInfoMissingJson, ohai_solo.system_info,
                          mock_ssh)

    def test_system_info_command_not_found(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.execute.return_value = {
            'exit_code': 1,
            'stdout': "",
            'stderr': "ohai-solo command not found"
        }
        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.system_info, mock_ssh)

    def test_system_info_could_not_find(self):
        mock_ssh = mock.MagicMock()
        mock_ssh.execute.return_value = {
            'exit_code': 1,
            'stdout': "",
            'stderr': "Could not find ohai-solo."
        }
        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.system_info, mock_ssh)


if __name__ == "__main__":
    unittest.main()
