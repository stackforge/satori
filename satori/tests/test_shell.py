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

"""Unit Tests for Shell module."""

import copy
import sys
import unittest

import fixtures
import mock
import six

from satori import errors
from satori import shell
from satori.tests import utils


if six.PY2:
    BUILTINS = "__builtin__"
else:
    BUILTINS = "builtins"


class TestTemplating(utils.TestCase):

    """Test Templating Code."""

    @mock.patch('%s.open' % BUILTINS)
    def test_get_template(self, mock_open):
        """Verify that get_template looks for the right template."""
        manager = mock_open.return_value.__enter__.return_value
        manager.read.return_value = 'some data'
        result = shell.get_template("foo")
        self.assertEqual(result, "some data")
        call_ = mock_open.call_args_list[0]
        args, _ = call_
        path, modifier = args
        self.assertTrue(path.endswith("/foo.jinja"))
        self.assertEqual(modifier, 'r')

    @mock.patch.object(shell, 'get_template')
    def test_output_results(self, mock_template):
        """Verify that output formatter parses supllied template."""
        mock_template.return_value = 'Output: {{ data.foo }}'
        result = shell.format_output("127.0.0.1", {'foo': 1})
        self.assertEqual(result, "Output: 1")

FAKE_ENV = {
    'OS_USERNAME': 'username',
    'OS_PASSWORD': 'password',
    'OS_TENANT_NAME': 'tenant_name',
    'OS_AUTH_URL': 'http://no.where'
}

FAKE_ENV2 = {
    'OS_USERNAME': 'username',
    'OS_PASSWORD': 'password',
    'OS_TENANT_ID': 'tenant_id',
    'OS_AUTH_URL': 'http://no.where'
}


class TestArgParsing(utils.TestCase):

    """Test Argument Parsing."""

    def setUp(self):
        super(TestArgParsing, self).setUp()
        self.mock_os = shell.os
        self.mock_os.environ = {}

    def make_env(self, exclude=None, fake_env=FAKE_ENV):
        """Create a patched os.environ.

        Borrowed from python-novaclient/novaclient/tests/test_shell.py.
        """

        env = dict((k, v) for k, v in fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    def run_shell(self, argstr, exitcodes=(0,)):
        """Simulate a user shell.

        Borrowed from python-novaclient/novaclient/tests/test_shell.py.
        """

        orig = sys.stdout
        orig_stderr = sys.stderr
        try:
            sys.stdout = six.StringIO()
            sys.stderr = six.StringIO()
            shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertIn(exc_value.code, exitcodes)
        finally:
            stdout = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig
            stderr = sys.stderr.getvalue()
            sys.stderr.close()
            sys.stderr = orig_stderr
        return (stdout, stderr)

    def test_missing_openstack_field_raises_argument_exception(self):
        """Verify that all 'required' OpenStack fields are needed.

        Iterate over the list of fields, remove one and verify that
        an exception is raised.
        """
        fields = [
            '--os-username=bob',
            '--os-password=secret',
            '--os-auth-url=http://domain.com/v1/auth',
            '--os-region-name=hawaii',
            '--os-tenant-name=bobs-better-burger',
        ]
        for i in range(len(fields)):
            fields_copy = copy.copy(fields)
            fields_copy.pop(i)
            fields_copy.append('domain.com')
            self.assertRaises(
                errors.SatoriShellException,
                self.run_shell,
                ' '.join(fields_copy),
                exitcodes=[0, 2]
            )

if __name__ == '__main__':
    unittest.main()
