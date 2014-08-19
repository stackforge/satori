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
# pylint: disable=C0111, C0103, W0212, R0904
"""Satori SSH Module Tests."""

import collections
import unittest

import mock

from satori import bash
from satori import errors
from satori.tests import utils


class TestBashModule(utils.TestCase):

    def setUp(self):
        super(TestBashModule, self).setUp()
        testrun = collections.namedtuple(
            "TestCmd", ["command", "stdout", "returncode"])
        self.testrun = testrun(
            command="echo hello", stdout="hello\n", returncode=0)
        self.resultdict = {'stdout': self.testrun.stdout.strip(),
                           'stderr': ''}


class TestLocalShell(TestBashModule):

    def setUp(self):
        super(TestLocalShell, self).setUp()
        popen_patcher = mock.patch.object(bash.subprocess, 'Popen')
        self.mock_popen = popen_patcher.start()
        mock_result = mock.MagicMock()
        mock_result.returncode = self.testrun.returncode
        self.mock_popen.return_value = mock_result
        mock_result.communicate.return_value = (self.testrun.stdout, '')
        self.localshell = bash.LocalShell()
        self.addCleanup(popen_patcher.stop)

    def test_execute(self):
        self.localshell.execute(self.testrun.command)
        self.mock_popen.assert_called_once_with(
            self.testrun.command.split(), cwd=None, stderr=-1, stdout=-1)

    def test_execute_resultdict(self):
        resultdict = self.localshell.execute(self.testrun.command)
        self.assertEqual(self.resultdict, resultdict)

    def test_execute_with_exit_code_resultdict(self):
        resultdict = self.localshell.execute(
            self.testrun.command, with_exit_code=True)
        self.resultdict.update({'exit_code': self.testrun.returncode})
        self.assertEqual(self.resultdict, resultdict)


@mock.patch.object(bash.utils, 'get_platform_info')
class TestLocalPlatformInfo(utils.TestCase):

    def test_is_debian(self, mock_gpi):
        mock_gpi.return_value = {'dist': 'Debian'}
        self.assertIsInstance(bash.LocalShell().is_debian(), bool)

    def test_is_fedora(self, mock_gpi):
        mock_gpi.return_value = {'dist': 'Fedora'}
        self.assertIsInstance(bash.LocalShell().is_fedora(), bool)

    def test_is_osx(self, mock_gpi):
        mock_gpi.return_value = {'dist': 'Darwin'}
        self.assertIsInstance(bash.LocalShell().is_windows(), bool)

    def test_is_windows(self, mock_gpi):
        mock_gpi.return_value = {'dist': 'Windows'}
        self.assertIsInstance(bash.LocalShell().is_osx(), bool)


class TestLocalPlatformInfoUndetermined(TestLocalShell):

    def setUp(self):
        blanks = {'dist': '', 'arch': '', 'version': ''}
        pinfo_patcher = mock.patch.object(
            bash.LocalShell, 'platform_info', new_callable=mock.PropertyMock)
        self.mock_platform_info = pinfo_patcher.start()
        self.mock_platform_info.return_value = blanks
        super(TestLocalPlatformInfoUndetermined, self).setUp()
        self.addCleanup(pinfo_patcher.stop)

    def test_is_debian(self):
        self.assertRaises(errors.UndeterminedPlatform,
                          self.localshell.is_debian)

    def test_is_fedora(self):
        self.assertRaises(errors.UndeterminedPlatform,
                          self.localshell.is_fedora)

    def test_is_osx(self):
        self.assertRaises(errors.UndeterminedPlatform,
                          self.localshell.is_osx)

    def test_is_windows(self):
        self.assertRaises(errors.UndeterminedPlatform,
                          self.localshell.is_windows)


class TestRemoteShell(TestBashModule):

    def setUp(self):
        super(TestRemoteShell, self).setUp()
        execute_patcher = mock.patch.object(bash.ssh.SSH, 'remote_execute')
        self.mock_execute = execute_patcher.start()
        self.mock_execute.return_value = self.resultdict
        self.remoteshell = bash.RemoteShell('192.168.2.10')
        self.addCleanup(execute_patcher.stop)

    def test_execute(self):
        self.remoteshell.execute(self.testrun.command)
        self.mock_execute.assert_called_once_with(
            self.testrun.command)

    def test_execute_resultdict(self):
        resultdict = self.remoteshell.execute(self.testrun.command)
        self.assertEqual(self.resultdict, resultdict)

    def test_execute_with_exit_code_resultdict(self):
        resultdict = self.remoteshell.execute(
            self.testrun.command, with_exit_code=True)
        self.resultdict.update({'exit_code': self.testrun.returncode})
        self.assertEqual(self.resultdict, resultdict)


class TestContextManager(utils.TestCase):

    def setUp(self):
        super(TestContextManager, self).setUp()
        connect_patcher = mock.patch.object(bash.RemoteShell, 'connect')
        close_patcher = mock.patch.object(bash.RemoteShell, 'close')
        self.mock_connect = connect_patcher.start()
        self.mock_close = close_patcher.start()
        self.addCleanup(connect_patcher.stop)
        self.addCleanup(close_patcher.stop)

    def test_context_manager(self):
        with bash.RemoteShell('192.168.2.10') as client:
            pass
        self.assertTrue(self.mock_connect.call_count == 1)
        # >=1 because __del__ (in most python implementations)
        # calls close()
        self.assertTrue(self.mock_close.call_count >= 1)

class TestIsDistro(TestRemoteShell):

    def setUp(self):
        super(TestIsDistro, self).setUp()
        self.platformdict = self.resultdict.copy()
        self.platformdict['stdout'] = str(bash.LocalShell().platform_info)

    def test_remote_platform_info(self):
        self.mock_execute.return_value = self.platformdict
        result = self.remoteshell.platform_info
        self.assertIsInstance(result, dict)
        self.assertTrue(all(k in result
                            for k in ('arch', 'dist', 'version')))
        assert self.mock_execute.called


if __name__ == "__main__":
    unittest.main()
