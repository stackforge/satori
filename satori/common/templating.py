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

"""Templating module."""

from __future__ import absolute_import

import json
import logging

import jinja2
from jinja2 import sandbox
import six

CODE_CACHE = {}
LOG = logging.getLogger(__name__)

if six.PY3:
    StandardError = Exception


class TemplateException(Exception):

    """Error applying template."""


class CompilerCache(jinja2.BytecodeCache):

    """Cache for compiled template code.

    This is leveraged when satori is used from within a long-running process,
    like a server. It does not speed things up for command-line use.
    """

    def load_bytecode(self, bucket):
        """Load compiled code from cache."""
        if bucket.key in CODE_CACHE:
            bucket.bytecode_from_string(CODE_CACHE[bucket.key])

    def dump_bytecode(self, bucket):
        """Write compiled code into cache."""
        CODE_CACHE[bucket.key] = bucket.bytecode_to_string()


def do_prepend(value, param='/'):
    """Prepend a string if the passed in string exists.

    Example:
    The template '{{ root|prepend('/')}}/path';
    Called with root undefined renders:
        /path
    Called with root defined as 'root' renders:
        /root/path
    """
    if value:
        return '%s%s' % (param, value)
    else:
        return ''


def preserve_linefeeds(value):
    """Escape linefeeds.

    To make templates work with both YAML and JSON, escape linefeeds instead of
    allowing Jinja to render them.
    """
    return value.replace("\n", "\\n").replace("\r", "")


def get_jinja_environment(template, extra_globals=None, **env_vars):
    """Return a sandboxed jinja environment."""
    template_map = {'template': template}
    env = sandbox.ImmutableSandboxedEnvironment(
        loader=jinja2.DictLoader(template_map),
        bytecode_cache=CompilerCache(), **env_vars)
    env.filters['prepend'] = do_prepend
    env.filters['preserve'] = preserve_linefeeds
    env.globals['json'] = json
    if extra_globals:
        env.globals.update(extra_globals)
    return env


def parse(template, extra_globals=None, env_vars=None, **kwargs):
    """Parse template.

    :param template: the template contents as a string
    :param extra_globals: additional globals to include
    :param kwargs: extra arguments are passed to the renderer
    """
    if env_vars is None:
        env_vars = {}
    env = get_jinja_environment(template, extra_globals=extra_globals,
                                **env_vars)

    minimum_kwargs = {
        'data': {},
    }
    minimum_kwargs.update(kwargs)

    try:
        template = env.get_template('template')
    except jinja2.TemplateSyntaxError as exc:
        LOG.error(exc, exc_info=True)
        error_message = "Template had a syntax error: %s" % exc
        raise TemplateException(error_message)

    try:
        result = template.render(**minimum_kwargs)
        # TODO(zns): exceptions in Jinja template sometimes missing traceback
    except jinja2.TemplateError as exc:
        LOG.error(exc, exc_info=True)
        error_message = "Template had an error: %s" % exc
        raise TemplateException(error_message)
    except StandardError as exc:
        LOG.error(exc, exc_info=True)
        error_message = "Template rendering failed: %s" % exc
        raise TemplateException(error_message)
    return result
