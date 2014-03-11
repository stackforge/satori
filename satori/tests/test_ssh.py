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
# pylint: disable=C0111, C0103
"""Satori SSH Module Tests."""

import os
import time
import unittest

from multiprocessing import pool

import mock
import paramiko

from satori import errors
from satori import ssh
from satori.tests import utils


class TestTTYRequired(utils.TestCase):

    """Test response to tty demand."""

    def setUp(self):

        super(TestTTYRequired, self).setUp()
        self.client = ssh.SSH('123.456.789.0', password='test_password')
        self.stdout = mock.MagicMock()
        self.stdin = mock.MagicMock()

    def test_valid_demand(self):
        """Ensure that anticipated requests for tty's return True."""
        for substring in ssh.TTY_REQUIRED:
            results = {'stdout': "xyz" + substring + "zyx"}
            self.assertTrue(self.client._handle_tty_required(results, False))

    def test_normal_response(self):
        """Ensure standard response returns False."""
        examples = ["hello", "#75-Ubuntu SMP Tue Jun 18 17:59:38 UTC 2013",
                    ("fatal: Not a git repository "
                     "(or any of the parent directories): .git")]
        for substring in examples:
            results = {'stderr': '', 'stdout': substring}
            self.assertFalse(self.client._handle_tty_required(results, False))

    def test_no_recurse(self):
        """Avoid infinte loop by raising GetPTYRetryFailure.

        When retrying with get_pty in response to one of TTY_REQUIRED
        """
        for substring in ssh.TTY_REQUIRED:
            results = {'stdout': substring}
            self.assertRaises(errors.GetPTYRetryFailure,
                              self.client._handle_tty_required,
                              results, True)


class TestSSHKeys(utils.TestCase):

    def setUp(self):
        super(TestSSHKeys, self).setUp()

        self.invalidkey = """
            -----BEGIN RSA PRIVATE KEY-----
            MJK7hkKYHUNJKDHNF)980BN456bjnkl_0Hj08,l$IRJSDLKjhkl/jFJVSLx2doRZ
            -----END RSA PRIVATE KEY-----
            """

        self.ecdsakey = """
            -----BEGIN EC PRIVATE KEY-----
            MHcCAQEEIIiZdMfDf+lScOkujN1+zAKDJ9PQRquCVZoXfS+6hDlToAoGCCqGSM49
            AwEHoUQDQgAE/qUj+vxnhIrkTR/ayYx9ZC/9JanJGyXkOe3Oe6WT/FJ9vBbfThTF
            U9+i43I3TONq+nWbhFKBj8XR4NKReaYeBw==
            -----END EC PRIVATE KEY-----
            """

        self.rsakey = """
            -----BEGIN RSA PRIVATE KEY-----
            MIIEowIBAAKCAQEAwbbaH5m0yLIVAi1i4aJ5uKprPM93x6b/KkH5N4QmZoXGOFId
            v0G64Sanz1VZkCWXiyivgkT6/y0+M0Ok8UK24UO6YNBSFGKboan/OMNETTIqXzmV
            liVYkQTf2zrBPWofjeDnzMndy7AD5iylJ6cNAksFM+sLt0MQcOeCmbOX8E6+AGZr
            JLj8orJgGJKU9jN5tnMlgtDP9BVrrbi7wX0kqb42OMtM6AuMUBDtAM2QSpTJa0JL
            mFOLfe6PYOLdQaJsnaoV+Wu4eBdY91h8COmhOKZv5VMYalOSDQnsKgngDW9iOoFs
            Uou7W8Wk3FXusbDwAvakWKmQtDF8SIgMLqygTwIDAQABAoIBAQCe5FkuKmm7ZTcO
            PiQpZ5fn/QFRM+vP/A64nrzI6MCGv5vDfreftU6Qd6CV1DBOqEcRgiHT/LjUrkui
            yQ12R36yb1dlKfrpdaiqhkIuURypJUjUKuuj6KYo7ZKgxCTVN0MCoUQBGmOvO4U3
            O8+MIt3sz5RI7bcCbyQBOCRL5p/uH3soWoG+6u2W17M4otLT0xJGX5eU0AoCYfOi
            Vd9Ot3j687k6KtZajy2hZIccuGNRwFeKSIAN9U7FEy4fgxkIMrc/wqArKmZLNui1
            SkVP3UHlbGVAI5ZDLzdcyxXPRWz1FBtJYiITtQCVKTv5LFCxFjlIWML2qJMB2GTW
            0+t1WhEhAoGBAOFdh14qn0i5v7DztpkS665vQ9F8n7RN0b17yK5wNmfhd4gYK/ym
            hCPUk0+JfPNQuhhhzoDXWICiCHRqNVT0ZzkyY0E2aTYLYxbeKkiCOccqJXxtxiI+
            6KneRMV3mKaJXJLz8G0YepB2Qhv4JkNsR1yiA5EqIs0Cr9Jafg9tHQsrAoGBANwL
            5lYjNHu51WVdjv2Db4oV26fRqAloc0//CBCl9IESM7m9A7zPTboMMijSqEuz3qXJ
            Fd5++B/b1Rkt4EunJNcE+XRJ9cI7MKE1kYKz6oiSN4X4eHQSDmlpS9DBcAEjTJ8r
            c+5DsPMSkz6qMxbG+FZB1SvVflFZe9dO8Ba7oR1tAoGAa+97keIf/5jW8k0HOzEQ
            p66qcH6bjqNmvLW4W7Nqmz4lHY1WI98skmyRURqsOWyEdIEDgjmhLZptKjRj7phP
            h9lWKDmDEltJzf4BilC0k2rgIUQCDQzMKe9GSL0K41gOemNS1y1OJjo9V1/2E3yc
            gQUnaDMiD8Ylpz2n+oNr0ZkCgYBqDK4g+2yS6JgI91MvqQW7lhc7xRZoGlfgyPe5
            FlJFVmFpdcf0WjCKptARzpzfhzuZyNTqW2T37bnBHdQIgfCGVFZpDjAMQPyJ5UhQ
            pqc01Ms/nOVogz9A3Ed2v5NcaQfHemiv/x2ruFsQi3R92LzczXOQYZ80U50Uwm2B
            d0IJ7QKBgD39jFiz7U4XEK/knRWUBUNq8QSGF5UuzO404z/+6J2KlFeNiDe+aH0c
            cdi+/PhkDkMXfW6eQdvgFYs277uss4M+4F8fWb2KVvPTuZXmTf6qntFoZNuL1oIv
            kn+fI2noF0ET7ktofoPEeD2/ya0B9/XecUqDJcVofoVO2pxMn12A
            -----END RSA PRIVATE KEY-----
            """

        self.dsakey = """
            -----BEGIN DSA PRIVATE KEY-----
            MIIBuwIBAAKBgQC+WvLRuPNDPVfZwKYqJYuD6XXjrUU4KIdLWmRO9qOtq0UR1kOQ
            /4rhjgb2TyujW6RzPnqPc9eUv84Z3gKawAdZv5/vKbp6tpMn86Y42r0Ohy63DEgM
            XyBfWxbZm0RBmLy3bCUefMOBngnODIhrTt2o+ip5ve5JMctDvjkWBVnZiQIVAMlh
            6gd7IC68FwynC4f/p8+zpx9pAoGARjTQeKxBBDDfxySYDN0maXHMR21RF/gklecO
            x6sH1MEDtOupQk0/uIPvolH0Jh+PK+NAv0GBZ96PDrF5z0S6MyQ5eHWGtwW4NFqk
            ZGHTriy+8qc4OhtyS3dpXQu40Ad2o1ap1v806RwM8iw1OfBa94h/vreedO0ij2Fe
            7aKEci4CgYAITw+ySCskHakn1GTG952MKxlMo7Mx++dYnCoFxsMwXFlwIrpzyhhC
            Qk11sEgcAOZ2HiRVhwaz4BivNV5iuwUeIeKJc12W4+FU+Lh533hFOcSAYbBr1Crl
            e+YpaOHRjLel0Nb5Cil4qEQaWQDmWvQb958IQQgzC9NhnR7NRNkfrgIVAKfMMZKz
            57plimt3W9YoDAATyr6i
            -----END DSA PRIVATE KEY-----
            """

    def test_invalid_key_raises_sshexception(self):
        self.assertRaises(
            paramiko.SSHException, ssh.SSH._get_pkey, self.invalidkey)

    def test_valid_ecdsa_returns_pkey_obj(self):
        self.assertIsInstance(ssh.SSH._get_pkey(self.ecdsakey), paramiko.PKey)

    def test_valid_rsa_returns_pkey_obj(self):
        self.assertIsInstance(ssh.SSH._get_pkey(self.rsakey), paramiko.PKey)

    def test_valid_ds_returns_pkey_obj(self):
        self.assertIsInstance(ssh.SSH._get_pkey(self.dsakey), paramiko.PKey)

    @mock.patch.object(ssh, 'LOG')
    def test_valid_ecdsa_logs_key_class(self, mock_LOG):
        ssh.SSH._get_pkey(self.ecdsakey)
        mock_LOG.info.assert_called_with(
            'Valid SSH Key provided (%s)', 'ECDSAKey')

    @mock.patch.object(ssh, 'LOG')
    def test_valid_rsa_logs_key_class(self, mock_LOG):
        ssh.SSH._get_pkey(self.rsakey)
        mock_LOG.info.assert_called_with(
                'Valid SSH Key provided (%s)', 'RSAKey')

    @mock.patch.object(ssh, 'LOG')
    def test_valid_dsa_logs_key_class(self, mock_LOG):
        ssh.SSH._get_pkey(self.dsakey)
        mock_LOG.info.assert_called_with(
                'Valid SSH Key provided (%s)', 'DSSKey')


class TestSSHConnect(TestSSHKeys):

    def setUp(self):
        super(TestSSHConnect, self).setUp()
        self.host = '123.456.789.0'
        self.client = ssh.SSH(self.host, username='test-user')
        paramiko.SSHClient.connect = mock.MagicMock()

    def test_connect_no_auth_attrs(self):
        """Test connect call without auth attributes."""
        self.client.connect()
        paramiko.SSHClient.connect.assert_called_once_with(
                '123.456.789.0', username='test-user',
                password=None, sock=None, port=22)

    def test_connect_with_password(self):
        self.client.password = 'test-password'
        self.client.connect()
        paramiko.SSHClient.connect.assert_called_once_with(
                '123.456.789.0', username='test-user',
                password='test-password', sock=None, port=22)

    def test_connect_invalid_private_key_string(self):
        self.client.private_key = self.invalidkey
        self.assertRaises(paramiko.SSHException, self.client.connect)

    def test_connect_valid_private_key_string(self):
        validkeys = [self.rsakey, self.dsakey, self.ecdsakey]
        for key in validkeys:
            self.client.private_key = key
            self.client.connect()
            pkey_kwarg_value = (paramiko.SSHClient.
                                connect.call_args[1]['pkey'])
            self.assertIsInstance(pkey_kwarg_value, paramiko.PKey)
            paramiko.SSHClient.connect.assert_called_with(
                    '123.456.789.0', username='test-user',
                    pkey=pkey_kwarg_value, sock=None, port=22, timeout=20)

    def test_key_filename(self):
        self.client.key_filename = "~/not/a/real/path"
        expanded_path = os.path.expanduser(self.client.key_filename)
        self.client.connect()
        paramiko.SSHClient.connect.assert_called_once_with(
            '123.456.789.0', username='test-user',
            key_filename=expanded_path,
            sock=None, port=22, timeout=20)

    def test_use_password_on_exc_negative(self):
        """Do this without self.password. """
        paramiko.SSHClient.connect.side_effect = (
                paramiko.PasswordRequiredException)
        self.assertRaises(paramiko.PasswordRequiredException,
                          self.client.connect)

    @mock.patch.object(ssh, 'LOG')
    def test_logging_use_password_on_exc_positive(self, mock_LOG):
        self.client.password = 'test-password'
        paramiko.SSHClient.connect.side_effect = (
                paramiko.PasswordRequiredException)
        self.assertRaises(paramiko.PasswordRequiredException,
                          self.client.connect)
        mock_LOG.debug.assert_called_with('Retrying with password credentials')

    @mock.patch.object(ssh, 'LOG')
    def test_logging_when_badhostkey(self, mock_LOG):
        """Test when raising BadHostKeyException."""
        self.client.private_key = self.rsakey
        paramiko.SSHClient.connect.side_effect = (
                paramiko.BadHostKeyException(None, None, None))
        self.assertRaises(paramiko.BadHostKeyException,
                          self.client.connect)
        mock_LOG.info.assert_called_with(
                "ssh://test-user@123.456.789.0:22 failed:  "
                "Host key for server None does not match!. "
                "You might have a bad key entry on your server, "
                "but this is a security issue and won't be handled "
                "automatically. To fix this you can remove the "
                "host entry for this host from the /.ssh/known_hosts file")

    @mock.patch.object(ssh, 'LOG')
    def test_logging_when_reraising_other_exc(self, mock_LOG):
        self.client.private_key = self.rsakey
        paramiko.SSHClient.connect.side_effect = Exception
        self.assertRaises(Exception,
                          self.client.connect)
        err = mock_LOG.info.call_args[0][-1]
        mock_LOG.info.assert_called_with(
            'ssh://%s@%s:%d failed.  %s',
            'test-user', '123.456.789.0', 22, err)

    def test_reraising_other_exc(self):
        self.client.private_key = self.rsakey
        paramiko.SSHClient.connect.side_effect = (
                paramiko.BadHostKeyException(None, None, None))
        self.assertRaises(paramiko.BadHostKeyException,
                          self.client.connect)

    def test_default_user_is_root(self):
        self.client = ssh.SSH('123.456.789.0')
        self.client.connect()
        default = paramiko.SSHClient.connect.call_args[1]['username']
        self.assertEqual(default, 'root')


class TestTestConnection(TestSSHKeys):

    def setUp(self):
        super(TestTestConnection, self).setUp()
        self.host = '123.456.789.0'
        self.client = ssh.SSH(self.host, username='test-user')
        paramiko.SSHClient.connect = mock.MagicMock()

    def test_test_connection(self):
        self.assertTrue(self.client.test_connection())

    def test_test_connection_fail_invalid_key(self):
        self.client.private_key = self.invalidkey
        self.assertFalse(self.client.test_connection())

    def test_test_connection_valid_key(self):
        self.client.private_key = self.dsakey
        self.assertTrue(self.client.test_connection())

    def test_test_connection_fail_other(self):
        paramiko.SSHClient.connect.side_effect = Exception
        self.assertFalse(self.client.test_connection())


class TestGetProxySocket(TestSSHKeys):

    def setUp(self):
        super(TestGetProxySocket, self).setUp()
        paramiko.ProxyCommand = mock.MagicMock()
        self.mutable = [True]
        paramiko.SSHClient.connect = mock.MagicMock()
        self.proxy = ssh.SSH('proxy.address', username='proxy-user')
        self.client = ssh.SSH('123.546.789.0', username='client-user')
        self.threadpool = pool.ThreadPool(processes=2)

    def tearDown(self):
        super(TestGetProxySocket, self).tearDown()
        self.threadpool.terminate()

    def test_get_proxy_socket(self):
        self.client._get_proxy_socket(self.proxy)
        paramiko.ProxyCommand.assert_called_once_with(
            'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 '
            ' -A proxy-user@proxy.address nc 123.546.789.0 22')

    def test_get_proxy_socket_private_key(self):
        self.proxy.private_key = self.rsakey
        self.client._get_proxy_socket(self.proxy)
        self.assertTrue(paramiko.ProxyCommand.called)

    def tempfile_spotted(self):
        home = os.path.expanduser('~/')
        filist = [k for k in os.listdir(home)
                  if k.startswith(ssh.TEMPFILE_PREFIX)]
        while all(self.mutable):
            new = [k for k in os.listdir(home)
                   if k.startswith(ssh.TEMPFILE_PREFIX)]
            if len(new) > len(filist):
                return set(new).difference(set(filist)).pop()
        return False

    def test_get_proxy_file_seen_and_removed(self):
        del self.mutable[:]
        self.mutable = [True]

        async_result = self.threadpool.apply_async(self.tempfile_spotted)
        time.sleep(.1)
        self.proxy.private_key = self.rsakey
        self.client._get_proxy_socket(self.proxy)
        temp = os.path.expanduser('~/%s' % async_result.get())
        paramiko.ProxyCommand.assert_called_once_with(
            'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 '
            ' -A proxy-user@proxy.address -i '
            '%s nc 123.546.789.0 22' % temp)

        self.assertFalse(os.path.exists(temp))

    def test_get_proxy_file_unseen(self):
        del self.mutable[:]
        self.mutable = [True]

        async_result = self.threadpool.apply_async(self.tempfile_spotted)
        self.proxy.key_filename = "~/not/a/real/path"
        expanded_path = os.path.expanduser(self.proxy.key_filename)
        self.client._get_proxy_socket(self.proxy)
        self.mutable.append(False)

        self.assertFalse(async_result.get())

        paramiko.ProxyCommand.assert_called_once_with(
            'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 '
            ' -A proxy-user@proxy.address -i %s '
            'nc 123.546.789.0 22' % expanded_path)


class TestPasswordPrompt(utils.TestCase):

    def setUp(self):
        super(TestPasswordPrompt, self).setUp()
        ssh.LOG = mock.MagicMock()
        self.client = ssh.SSH('123.456.789.0', password='test_password')
        self.stdout = mock.MagicMock()
        self.stdin = mock.MagicMock()

    def test_channel_closed(self):
        """If the channel is closed, there's no prompt."""
        self.stdout.channel.closed = True
        self.assertFalse(
            self.client._handle_password_prompt(self.stdin, self.stdout))

    def test_password_prompt_buflen_too_short(self):
        """Stdout chan buflen is too short to be a password prompt."""
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "a" * (ssh.MIN_PASSWORD_PROMPT_LEN - 1)
        self.assertFalse(
            self.client._handle_password_prompt(self.stdin, self.stdout))

    def test_password_prompt_buflen_too_long(self):
        """Stdout chan buflen is too long to be a password prompt."""
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "a" * (ssh.MAX_PASSWORD_PROMPT_LEN + 1)
        self.assertFalse(
            self.client._handle_password_prompt(self.stdin, self.stdout))

    def test_common_password_prompt(self):
        """Ensure that a couple commonly seen prompts have success."""
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "[sudo] password for user:"
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.assertTrue(
            self.client._handle_password_prompt(self.stdin, self.stdout))
        self.stdout.channel.in_buffer = "Password:"
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.assertTrue(
            self.client._handle_password_prompt(self.stdin, self.stdout))

    def test_password_prompt_other_prompt(self):
        """Pass buflen check, fail on substring check."""
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "Welcome to <hostname>:"
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.assertFalse(
            self.client._handle_password_prompt(self.stdin, self.stdout))

    def test_logging_encountered_prompt(self):
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "[sudo] password for user:"
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.client._handle_password_prompt(self.stdin, self.stdout)
        ssh.LOG.warning.assert_called_with(
            '%s@%s encountered prompt! of length  [%s] {%s}', "root",
            '123.456.789.0', 25, '[sudo] password for user:')

    def test_logging_nearly_false_positive(self):
        """Assert that a close-call on a false-positive logs a warning."""
        other_prompt = "Welcome to <hostname>:"
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = other_prompt
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.client._handle_password_prompt(self.stdin, self.stdout)
        ssh.LOG.warning.assert_called_with(
            'Nearly a False-Positive on password prompt detection. [%s] {%s}',
            22, other_prompt)

    def test_password_given_to_prompt(self):
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "[sudo] password for user:"
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.client._handle_password_prompt(self.stdin, self.stdout)
        self.stdin.write.assert_called_with(self.client.password + '\n')

    def test_password_given_returns_true(self):
        self.stdout.channel.closed = False
        self.stdout.channel.in_buffer = "[sudo] password for user:"
        self.stdout.channel.recv.return_value = self.stdout.channel.in_buffer
        self.assertTrue(
            self.client._handle_password_prompt(self.stdin, self.stdout))


if __name__ == "__main__":
    unittest.main()
