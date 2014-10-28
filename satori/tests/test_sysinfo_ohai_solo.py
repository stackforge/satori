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
    @mock.patch.object(ohai_solo, 'perform_install')
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
            mock_bash.RemoteShell().__enter__.return_value)

        mock_bash.RemoteShell.assert_any_call(
            address, username="bar",
            private_key="foo",
            interactive=False)
        mock_sysinfo.assert_called_with(
            mock_bash.RemoteShell().__enter__.return_value)


class TestOhaiInstall(utils.TestCase):

    def setUp(self):
        super(TestOhaiInstall, self).setUp()
        self.mock_remotesshclient = mock.MagicMock()
        self.mock_remotesshclient.is_windows.return_value = False

    def test_perform_install_fedora(self):
        response = {'exit_code': 0, 'stdout': 'installed remote'}
        self.mock_remotesshclient.execute.return_value = response
        result = ohai_solo.perform_install(self.mock_remotesshclient)
        self.assertEqual(result, response)
        self.assertEqual(self.mock_remotesshclient.execute.call_count, 3)
        self.mock_remotesshclient.execute.assert_has_calls([
            mock.call('wget -N http://readonly.configdiscovery.rackspace.com/install.sh', cwd='/tmp',
                      escalate=True, allow_many=False),
            mock.call('bash install.sh', cwd='/tmp', with_exit_code=True,
                      escalate=True, allow_many=False),
            mock.call('rm install.sh', cwd='/tmp', escalate=True,
                      allow_many=False)])

    def test_install_linux_remote_failed(self):
        response = {'exit_code': 1, 'stdout': "", "stderr": "FAIL"}
        self.mock_remotesshclient.execute.return_value = response
        self.assertRaises(errors.SystemInfoCommandInstallFailed,
                          ohai_solo.perform_install, self.mock_remotesshclient)


class TestOhaiRemove(utils.TestCase):

    def setUp(self):
        super(TestOhaiRemove, self).setUp()
        self.mock_remotesshclient = mock.MagicMock()
        self.mock_remotesshclient.is_windows.return_value = False

    def test_remove_remote_fedora(self):
        self.mock_remotesshclient.is_debian.return_value = False
        self.mock_remotesshclient.is_fedora.return_value = True
        response = {'exit_code': 0, 'foo': 'bar'}
        self.mock_remotesshclient.execute.return_value = response
        result = ohai_solo.remove_remote(self.mock_remotesshclient)
        self.assertEqual(result, response)
        self.mock_remotesshclient.execute.assert_called_once_with(
            'yum -y erase ohai-solo', cwd='/tmp', escalate=True)

    def test_remove_remote_debian(self):
        self.mock_remotesshclient.is_debian.return_value = True
        self.mock_remotesshclient.is_fedora.return_value = False
        response = {'exit_code': 0, 'foo': 'bar'}
        self.mock_remotesshclient.execute.return_value = response
        result = ohai_solo.remove_remote(self.mock_remotesshclient)
        self.assertEqual(result, response)
        self.mock_remotesshclient.execute.assert_called_once_with(
            'dpkg --purge ohai-solo', cwd='/tmp', escalate=True)

    def test_remove_remote_unsupported(self):
        self.mock_remotesshclient.is_debian.return_value = False
        self.mock_remotesshclient.is_fedora.return_value = False
        self.assertRaises(errors.UnsupportedPlatform,
                          ohai_solo.remove_remote, self.mock_remotesshclient)


class TestSystemInfo(utils.TestCase):

    def setUp(self):
        super(TestSystemInfo, self).setUp()
        self.mock_remotesshclient = mock.MagicMock()
        self.mock_remotesshclient.is_windows.return_value = False

    def test_system_info(self):
        self.mock_remotesshclient.execute.return_value = {
            'exit_code': 0,
            'stdout': "{}",
            'stderr': ""
        }
        ohai_solo.system_info(self.mock_remotesshclient)
        self.mock_remotesshclient.execute.assert_called_with(
            "unset GEM_CACHE GEM_HOME GEM_PATH && sudo ohai-solo",
            escalate=True, allow_many=False)

    def test_system_info_with_motd(self):
        self.mock_remotesshclient.execute.return_value = {
            'exit_code': 0,
            'stdout': "Hello world\n {}",
            'stderr': ""
        }
        ohai_solo.system_info(self.mock_remotesshclient)
        self.mock_remotesshclient.execute.assert_called_with(
            "unset GEM_CACHE GEM_HOME GEM_PATH && sudo ohai-solo",
            escalate=True, allow_many=False)

    def test_system_info_bad_json(self):
        self.mock_remotesshclient.execute.return_value = {
            'exit_code': 0,
            'stdout': "{Not JSON!}",
            'stderr': ""
        }
        self.assertRaises(errors.SystemInfoNotJson, ohai_solo.system_info,
                          self.mock_remotesshclient)

    def test_system_info_missing_json(self):
        self.mock_remotesshclient.execute.return_value = {
            'exit_code': 0,
            'stdout': "No JSON!",
            'stderr': ""
        }
        self.assertRaises(errors.SystemInfoMissingJson, ohai_solo.system_info,
                          self.mock_remotesshclient)

    def test_system_info_command_not_found(self):
        self.mock_remotesshclient.execute.return_value = {
            'exit_code': 1,
            'stdout': "",
            'stderr': "ohai-solo command not found"
        }
        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.system_info, self.mock_remotesshclient)

    def test_system_info_could_not_find(self):
        self.mock_remotesshclient.execute.return_value = {
            'exit_code': 1,
            'stdout': "",
            'stderr': "Could not find ohai-solo."
        }
        self.assertRaises(errors.SystemInfoCommandMissing,
                          ohai_solo.system_info, self.mock_remotesshclient)


if __name__ == "__main__":
    unittest.main()
