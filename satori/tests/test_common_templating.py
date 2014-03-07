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


def fail_fixture():
    """Used to simulate a template error."""
    raise AttributeError("Boom!")


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

    def test_template_extra_globals(self):
        """Globals are available in template."""
        result = templating.parse("{{ foo }}", foo="bar")
        self.assertEqual(result, 'bar')

    def test_template_syntax_error(self):
        """jinja.TemplateSyntaxError is caught."""
        with self.assertRaises(templating.TemplateException):
            templating.parse("{{ not closed")

    def test_template_undefined_error(self):
        """jinja.UndefinedError is caught."""
        with self.assertRaises(templating.TemplateException):
            templating.parse("{{ unknown() }}")

    def test_template_exception(self):
        """Exception in global is caught."""
        with self.assertRaises(templating.TemplateException):
            templating.parse("{{ boom() }}", boom=fail_fixture)

    def test_extra_globals(self):
        """Validates globals are set."""
        env = templating.get_jinja_environment("", {'foo': 1})
        self.assertIn('foo', env.globals)
        self.assertEqual(env.globals['foo'], 1)

    def test_json_included(self):
        """json library available to template."""
        result = templating.parse("{{ json.dumps({'data': 1}) }}")
        self.assertEqual(result, '{"data": 1}')


if __name__ == '__main__':
    unittest.main()
