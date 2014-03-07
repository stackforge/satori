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

"""Unit Tests for Templating module."""

import unittest

from satori.common import templating


class TestTemplating(unittest.TestCase):

    """Test Templating Module."""

    def test_prepend_function(self):
        """preserve returns escaped linefeeds."""
        result = templating.parse("{{ root|prepend('/')}}/path", root="etc")
        self.assertEqual(result, '/etc/path')

    def test_prepend_function_blank(self):
        """preserve returns escaped linefeeds."""
        result = templating.parse("{{ root|prepend('/')}}/path")
        self.assertEqual(result, '/path')

    def test_preserve_linefeed_escaping(self):
        """preserve returns escaped linefeeds."""
        result = templating.parse('{{ "A\nB" | preserve }}')
        self.assertEqual(result, 'A\\nB')


if __name__ == '__main__':
    unittest.main()
