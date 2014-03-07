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

"""Unit Tests for Shell module."""

import os
import unittest

import mock

from satori import shell


class TestTemplating(unittest.TestCase):

    """Test Templating Code."""

    @mock.patch('__builtin__.open')
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


if __name__ == '__main__':
    unittest.main()
