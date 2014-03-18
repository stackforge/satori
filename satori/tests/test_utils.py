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

"""Tests for utils module."""

import datetime
import time
import unittest

import mock

from satori import utils


class SomeTZ(datetime.tzinfo):

    """A random timezone."""

    def utcoffset(self, dt):
            return datetime.timedelta(minutes=45)

    def tzname(self, dt):
            return "STZ"

    def dst(self, dt):
            return datetime.timedelta(0)


class TestTimeUtils(unittest.TestCase):

    """Test time formatting functions."""

    def test_get_formatted_time_string(self):
        some_time = time.gmtime(0)
        with mock.patch.object(utils.time, 'gmtime') as mock_gmt:
            mock_gmt.return_value = some_time
            result = utils.get_time_string()
            self.assertEqual(result, "1970-01-01 00:00:00 +0000")

    def test_get_formatted_time_string_time_struct(self):
        result = utils.get_time_string(time_obj=time.gmtime(0))
        self.assertEqual(result, "1970-01-01 00:00:00 +0000")

    def test_get_formatted_time_string_datetime(self):
        result = utils.get_time_string(
            time_obj=datetime.datetime(1970, 2, 1, 1, 2, 3, 0))
        self.assertEqual(result, "1970-02-01 01:02:03 +0000")

    def test_get_formatted_time_string_datetime_tz(self):
        result = utils.get_time_string(
            time_obj=datetime.datetime(1970, 2, 1, 1, 2, 3, 0, SomeTZ()))
        self.assertEqual(result, "1970-02-01 01:47:03 +0000")

    def test_parse_time_string(self):
        result = utils.parse_time_string("1970-02-01 01:02:03 +0000")
        self.assertEqual(result, datetime.datetime(1970, 2, 1, 1, 2, 3, 0))

    def test_parse_time_string_with_tz(self):
        result = utils.parse_time_string("1970-02-01 01:02:03 +1000")
        self.assertEqual(result, datetime.datetime(1970, 2, 1, 11, 2, 3, 0))


class TestGetSource(unittest.TestCase):

    def setUp(self):
        self.code_string = ('the_problem = "not the problem"\n'
                            'return the_problem\n')

    def get_my_source_one_line_docstring(self):
        """A beautiful docstring."""
        the_problem = "not the problem"
        return the_problem

    def get_my_source_multiline_docstring(self):
        """A beautiful docstring.

        Is a terrible thing to waste.
        """
        the_problem = "not the problem"
        return the_problem

    def test_get_source(self):
        nab = utils.get_source_body(self.get_my_source_one_line_docstring)
        self.assertEqual(self.code_string, nab)

    def test_get_source_with_docstring(self):
        nab = utils.get_source_body(self.get_my_source_one_line_docstring,
                                    with_docstring=True)
        copy = '"""A beautiful docstring."""\n' + self.code_string
        self.assertEqual(copy, nab)

    def test_get_source_with_multiline_docstring(self):
        nab = utils.get_source_body(self.get_my_source_multiline_docstring,
                                    with_docstring=True)
        copy = ('"""A beautiful docstring.\n\n'
                'Is a terrible thing to waste.\n"""\n' + self.code_string)
        self.assertEqual(copy, nab)


if __name__ == '__main__':
    unittest.main()
