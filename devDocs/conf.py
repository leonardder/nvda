#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2019 NV Access Limited, Leonard de RUijter
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('../source'))
import sourceEnv

# Initialize languageHandler so that sphinx is able to deal with translatable strings.
import languageHandler
languageHandler.setLanguage("en")

# Initialize globalvars.appArgs to something sensible.
import globalVars
class AppArgs:
	# Set an empty comnfig path
	# This is never used as we don't initialize config, but some modules expect this to be set.
	configPath = ""
	secure = False
	disableAddons = True
	launcher = False
globalVars.appArgs = AppArgs()

# Import NVDA's versionInfo module.
import versionInfo
# Set a suitable updateVersionType for the updateCheck module to be imported
versionInfo.updateVersionType = "stable"

# -- Project information -----------------------------------------------------

project = versionInfo.name
copyright = versionInfo.copyright
author = versionInfo.publisher

# The major project version
version  = versionInfo.formatVersionForGUI(versionInfo.version_year, versionInfo.version_major, versionInfo.version_minor)

# The full version, including alpha/beta/rc tags
release = versionInfo.version

# -- General configuration ---------------------------------------------------

default_role = 'py:obj'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
	'sphinx.ext.autodoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
	"_build"
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.

html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

# sphinx.ext.autodoc configuration

autoclass_content = "both" # Both the class’ and the __init__ method’s docstring are concatenated and inserted.
autodoc_member_order = 'bysource'
autodoc_mock_imports = [
	"louis", # Not our project
]

# Perform some manual mocking of specific objects.
# autodoc can only mock modules, not objects.
from sphinx.ext.autodoc.mock import _make_subclass

import config
# Mock an instance of the configuration manager.
config.conf = _make_subclass("conf","config")()

# Support for auto generation of API docs
# Based on code published in https://github.com/readthedocs/readthedocs.org/issues/1139#issuecomment-398083449

def run_apidoc(_):
	ignore_paths = [
		'_buildVersion.py',
		'comInterfaces',
		'images',
		'lib',
		'lib64',
		'libArm64',
		'locale',
		'louis', # Not our project
		'typelibs',
		'waves',
		"mathType.py", # Fails when not installed
		'oleTypes.py', # Not our code
		'setup.py', # Py2exe
		'sourceEnv.py', # Only available when running from source
	]
	argv = [
		#"--force", # overwrite existing files
		"-P", # Include private modules
		"--module-first", # put module documentation before submodule documentation
		"--output-dir", ".",
		sys.path[0] # Module sources
	] + [os.path.join(sys.path[0], path) for path in ignore_paths]

	from sphinx.ext import apidoc
	apidoc.main(argv)

def setup(app):
	app.connect('builder-inited', run_apidoc)
