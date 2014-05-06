# -*- coding: utf-8 -*-
#
# OpenStack Configuration Discovery documentation build configuration file, created
# by sphinx-quickstart on Wed May 16 12:05:58 2012.
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import glob
import os
import re
import sys

import pbr.version

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
CONTRIB_DIR = os.path.join(ROOT, 'contrib')
PLUGIN_DIRS = glob.glob(os.path.join(CONTRIB_DIR, '*'))

sys.path.insert(0, ROOT)
sys.path.insert(0, BASE_DIR)
sys.path = PLUGIN_DIRS + sys.path


#
# Automatically write module docs
#
def write_autodoc_index():

    def get_contrib_sources():
        module_dirs = glob.glob(os.path.join(CONTRIB_DIR, '*'))
        module_names = map(os.path.basename, module_dirs)

        return dict(
            ('contrib/%s' % module_name,
             {'module': module_name,
              'path': os.path.join(CONTRIB_DIR, module_name)}
             )
            for module_name in module_names)

    def find_autodoc_modules(module_name, sourcedir):
        """Return a list of modules in the SOURCE directory."""
        modlist = []
        os.chdir(os.path.join(sourcedir, module_name))
        print("SEARCHING %s" % sourcedir)
        for root, dirs, files in os.walk("."):
            for filename in files:
                if filename.endswith(".py"):
                    # remove the pieces of the root
                    elements = root.split(os.path.sep)
                    # replace the leading "." with the module name
                    elements[0] = module_name
                    # and get the base module name
                    base, extension = os.path.splitext(filename)
                    if not (base == "__init__"):
                        elements.append(base)
                    result = ".".join(elements)
                    modlist.append(result)
        return modlist

    RSTDIR = os.path.abspath(os.path.join(BASE_DIR, "sourcecode"))
    SRCS = {'satori': {'module': 'satori',
                       'path': ROOT}}
    SRCS.update(get_contrib_sources())

    EXCLUDED_MODULES = ('satori.doc',
                        '.*\.tests')
    CURRENT_SOURCES = {}

    if not(os.path.exists(RSTDIR)):
        os.mkdir(RSTDIR)
    CURRENT_SOURCES[RSTDIR] = ['autoindex.rst', '.gitignore']

    INDEXOUT = open(os.path.join(RSTDIR, "autoindex.rst"), "w")
    INDEXOUT.write("=================\n")
    INDEXOUT.write("Source Code Index\n")
    INDEXOUT.write("=================\n")

    for title, info in SRCS.items():
        path = info['path']
        modulename = info['module']
        sys.stdout.write("Generating source documentation for %s\n" %
                         title)
        INDEXOUT.write("\n%s\n" % title.capitalize())
        INDEXOUT.write("%s\n" % ("=" * len(title),))
        INDEXOUT.write(".. toctree::\n")
        INDEXOUT.write("   :maxdepth: 1\n")
        INDEXOUT.write("\n")

        MOD_DIR = os.path.join(RSTDIR, title)
        CURRENT_SOURCES[MOD_DIR] = []
        if not(os.path.exists(MOD_DIR)):
            os.makedirs(MOD_DIR)
        for module in find_autodoc_modules(modulename, path):
            if any([re.match(exclude, module)
                    for exclude
                    in EXCLUDED_MODULES]):
                print("Excluded module %s." % module)
                continue
            mod_path = os.path.join(path, *module.split("."))
            generated_file = os.path.join(MOD_DIR, "%s.rst" % module)

            INDEXOUT.write("   %s/%s\n" % (title, module))

            # Find the __init__.py module if this is a directory
            if os.path.isdir(mod_path):
                source_file = ".".join((os.path.join(mod_path, "__init__"),
                                        "py",))
            else:
                source_file = ".".join((os.path.join(mod_path), "py"))

            CURRENT_SOURCES[MOD_DIR].append("%s.rst" % module)
            # Only generate a new file if the source has changed or we don't
            # have a doc file to begin with.
            if not os.access(generated_file, os.F_OK) or \
                    os.stat(generated_file).st_mtime < \
                    os.stat(source_file).st_mtime:
                print("Module %s updated, generating new documentation."
                      % module)
                FILEOUT = open(generated_file, "w")
                header = "The :mod:`%s` Module" % module
                FILEOUT.write("%s\n" % ("=" * len(header),))
                FILEOUT.write("%s\n" % header)
                FILEOUT.write("%s\n" % ("=" * len(header),))
                FILEOUT.write(".. automodule:: %s\n" % module)
                FILEOUT.write("  :members:\n")
                FILEOUT.write("  :undoc-members:\n")
                FILEOUT.write("  :show-inheritance:\n")
                FILEOUT.write("  :noindex:\n")
                FILEOUT.close()

    INDEXOUT.close()

    # Delete auto-generated .rst files for sources which no longer exist
    for directory, subdirs, files in list(os.walk(RSTDIR)):
        for old_file in files:
            if old_file not in CURRENT_SOURCES.get(directory, []):
                print("Removing outdated file for %s" % old_file)
                os.remove(os.path.join(directory, old_file))

write_autodoc_index()


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.ifconfig',
              'sphinx.ext.viewcode',
              'sphinx.ext.todo',
              'sphinx.ext.coverage',
              'sphinx.ext.pngmath',
              'sphinx.ext.viewcode',
              'sphinx.ext.doctest']

todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
if os.getenv('HUDSON_PUBLISH_DOCS'):
    templates_path = ['_ga', '_templates']
else:
    templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Satori'
copyright = u'2012-2013 OpenStack Foundation'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
version_info = pbr.version.VersionInfo('satori')
#
# The short X.Y version.
version = version_info.version_string()
# The full version, including alpha/beta/rc tags.
release = version_info.release_string()

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['**/#*', '**~', '**/#*#']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

primary_domain = 'py'
nitpicky = False


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "nosidebar": "false"
}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'
git_cmd = "git log --pretty=format:'%ad, commit %h' --date=local -n1"
html_last_updated_fmt = os.popen(git_cmd).read()

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Satoridoc'



# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual])
# .
latex_documents = [
    ('index', 'Satori.tex',
     u'OpenStack Configuration Discovery Documentation',
     u'OpenStack', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        'man/satori',
        'satori',
        u'OpenStack Configuration Discovery',
        [u'OpenStack contributors'],
        1,
    ),
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'OpenStackConfigurationDiscovery',
     u'OpenStack Configuration Discovery Documentation',
     u'OpenStack', 'OpenStackConfigurationDiscovery',
     'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}
