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
"""General utilities.

- Class and module import/export
- Time utilities (we standardize on UTC)
"""

import datetime
import logging
import sys
import time

import iso8601

LOG = logging.getLogger(__name__)
STRING_FORMAT = "%Y-%m-%d %H:%M:%S +0000"


def import_class(import_str):
    """Return a class from a string including module and class."""
    mod_str, _, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ImportError, ValueError, AttributeError) as exc:
        LOG.debug('Inner Exception: %s', exc)
        raise


def import_object(import_str, *args, **kw):
    """Return an object including a module or module and class."""
    try:
        __import__(import_str)
        return sys.modules[import_str]
    except ImportError:
        cls = import_class(import_str)
        return cls(*args, **kw)


def get_time_string(time_obj=None):
    """The canonical time string format (in UTC).

    :param time_obj: an optional datetime.datetime or timestruct (defaults to
                     gm_time)

    Note: Changing this function will change all times that this project uses
    in the returned data.
    """
    if isinstance(time_obj, datetime.datetime):
        if time_obj.tzinfo:
            offset = time_obj.tzinfo.utcoffset(time_obj)
            utc_dt = time_obj + offset
            return datetime.datetime.strftime(utc_dt, STRING_FORMAT)
        return datetime.datetime.strftime(time_obj, STRING_FORMAT)
    elif isinstance(time_obj, time.struct_time):
        return time.strftime(STRING_FORMAT, time_obj)
    elif time_obj is not None:
        raise TypeError("get_time_string takes only a time_struct, none, or a "
                        "datetime. It was given a %s" % type(time_obj))
    return time.strftime(STRING_FORMAT, time.gmtime())


def parse_time_string(time_string):
    """Return naive datetime object from string in standard time format."""
    parsed = time_string.replace(" +", "+").replace(" -", "-")
    dt_with_tz = iso8601.parse_date(parsed)
    offset = dt_with_tz.tzinfo.utcoffset(dt_with_tz)
    result = dt_with_tz + offset
    return result.replace(tzinfo=None)
