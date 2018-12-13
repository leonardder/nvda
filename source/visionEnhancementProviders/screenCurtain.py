#visionEnhancementProviders/screenCurtain.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2018 NV Access Limited

"""Screen curtain implementation based on the windows magnification API."""

from vision import ColorEnhancer, ColorTransformationInfo, ROLE_MAGNIFIER, ROLE_HIGHLIGHTER
import winVersion
try:
	import winMagnification
except AttributeError:
	if not winVersion.isFullScreenMagnificationAvailable():
		raise RuntimeError("This module is only supported on Windows 8 and above")
	raise
from ctypes import byref
from collections import OrderedDict

TRANSFORM_BLACK = winMagnification.MAGCOLOREFFECT()
TRANSFORM_BLACK.transform[4][4] = 1.0
TRANSFORM_DEFAULT = winMagnification.MAGCOLOREFFECT()
TRANSFORM_DEFAULT.transform[0][0] = 1.0
TRANSFORM_DEFAULT.transform[1][1] = 1.0
TRANSFORM_DEFAULT.transform[2][2] = 1.0
TRANSFORM_DEFAULT.transform[3][3] = 1.0
TRANSFORM_DEFAULT.transform[4][4] = 1.0

class VisionEnhancementProvider(ColorEnhancer):
	"""Screen curtain implementation based on the windows magnification API.
	This is only supported on Windows 8 and abbove."""
	name = "screenCurtain"
	# Translators: Description of a vision enhancement provider that disables output to the screen,
	# making it black.
	description = _("Screen Curtain")
	conflictingRoles = frozenset([ROLE_MAGNIFIER, ROLE_HIGHLIGHTER])

	def __init__(self, *roles):
		winMagnification.Initialize()
		super(VisionEnhancementProvider, self).__init__(*roles)

	def _getAvailableTransformations(self):
		return [
			ColorTransformationInfo("black", pgettext('color hue','black'), TRANSFORM_BLACK),
			# Translators: The state when the screen curtain is disabled.
			ColorTransformationInfo("off", _("disabled"), TRANSFORM_DEFAULT),
		]

	def initializeColorEnhancer(self):
		super(VisionEnhancementProvider, self).initializeColorEnhancer()
		self.transformation = "black"

	def _get_transformation(self):
		return self._transformation

	def _set_transformation(self, transformation):
		info = self.availableTransformations[transformation]
		winMagnification.SetFullscreenColorEffect(byref(info.value))
		self._transformation = transformation

	def terminateColorEnhancer(self):
		self.transformation = "off"
		super(VisionEnhancementProvider, self).terminateColorEnhancer()

	def terminate(self, *roles):
		super(VisionEnhancementProvider, self).terminate(*roles)
		winMagnification.Uninitialize()
