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
	'autoapi.extension',
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

html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

autoapi_dirs = ['../source']
