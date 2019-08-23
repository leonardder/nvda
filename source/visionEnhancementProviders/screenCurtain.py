# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2018-2019 NV Access Limited, Babbage B.V., Leonard de Ruijter

"""Screen curtain implementation based on the windows magnification API.
This implementation only works on Windows 8 and above.
"""

import vision
import winVersion
from ctypes import Structure, windll, c_float, POINTER, WINFUNCTYPE, WinError
from ctypes.wintypes import BOOL
import driverHandler
import wx
import gui
import config


class MAGCOLOREFFECT(Structure):
	_fields_ = (("transform", c_float * 5 * 5),)


TRANSFORM_BLACK = MAGCOLOREFFECT()
TRANSFORM_BLACK.transform[4][4] = 1.0


def _errCheck(result, func, args):
	if result == 0:
		raise WinError()
	return args


class Magnification:
	"""Singleton that wraps necessary functions from the Windows magnification API."""

	_magnification = windll.Magnification

	_MagInitializeFuncType = WINFUNCTYPE(BOOL)
	_MagUninitializeFuncType = WINFUNCTYPE(BOOL)
	_MagSetFullscreenColorEffectFuncType = WINFUNCTYPE(BOOL, POINTER(MAGCOLOREFFECT))
	_MagSetFullscreenColorEffectArgTypes = ((1, "effect"),)
	_MagGetFullscreenColorEffectFuncType = WINFUNCTYPE(BOOL, POINTER(MAGCOLOREFFECT))
	_MagGetFullscreenColorEffectArgTypes = ((2, "effect"),)

	MagInitialize = _MagInitializeFuncType(("MagInitialize", _magnification))
	MagInitialize.errcheck = _errCheck
	MagUninitialize = _MagUninitializeFuncType(("MagUninitialize", _magnification))
	MagUninitialize.errcheck = _errCheck
	try:
		MagSetFullscreenColorEffect = _MagSetFullscreenColorEffectFuncType(
			("MagSetFullscreenColorEffect", _magnification),
			_MagSetFullscreenColorEffectArgTypes
		)
		MagSetFullscreenColorEffect.errcheck = _errCheck
		MagGetFullscreenColorEffect = _MagGetFullscreenColorEffectFuncType(
			("MagGetFullscreenColorEffect", _magnification),
			_MagGetFullscreenColorEffectArgTypes
		)
		MagGetFullscreenColorEffect.errcheck = _errCheck
	except AttributeError:
		MagSetFullscreenColorEffect = None
		MagGetFullscreenColorEffect = None


class VisionEnhancementProvider(vision.providerBase.VisionEnhancementProvider):
	name = "screenCurtain"
	# Translators: Description of a vision enhancement provider that disables output to the screen,
	# making it black.
	description = _("Screen Curtain")
	supportedRoles = frozenset([vision.constants.Role.COLORENHANCER])

	# Default settings for parameters
	warnOnLoad = True

	# Translators: A warning shown when activating the screen curtain.
	# {description} is replaced by the translation of "screen curtain"
	warnOnLoadText = _(
		f"You have enabled {description}.\n"
		f"When {description} is enabled, the screen of your computer will be completely black.\n"
		"While this hides your screen's contents for sighted people, "
		"it might get you in a lost state whenever NVDA freezes.\n"
		f"Do you really want to enable {description}?"
	)

	supportedSettings = [
		driverHandler.BooleanDriverSetting(
			"warnOnLoad",
			# Translators: Description for a screen curtain setting that shows a warning when loading
			# the screen curtain.
			_(f"Show a warning when {description} is loaded"),
			defaultVal=warnOnLoad
		),
	]

	@classmethod
	def canStart(cls):
		return winVersion.isFullScreenMagnificationAvailable()

	def __init__(self):
		super(VisionEnhancementProvider, self).__init__()
		Magnification.MagInitialize()
		# Execute postInit with a CallAfter to ensure that the config spec is coupled with the config section.
		# It also allows us to show a message box and ensures that happens on the main thread.
		wx.CallAfter(self.postInit)

	def postInit(self):
		if self.warnOnLoad:
			parent = next(
				(
					dlg for dlg, state in gui.settingsDialogs.NVDASettingsDialog._instances.items()
					if isinstance(dlg, gui.settingsDialogs.NVDASettingsDialog)
					and state == gui.settingsDialogs.SettingsDialog._DIALOG_CREATED_STATE
				),
				gui.mainFrame
			)
			res = WarnOnLoadDialog(
				parent=parent,
				# Translators: Title for the screen curtain warning dialog.
				title=_("Warning"),
				message=self.warnOnLoadText,
				dialogType=WarnOnLoadDialog.DIALOG_TYPE_WARNING
			).ShowModal()
			if res == wx.NO:
				return
		Magnification.MagSetFullscreenColorEffect(TRANSFORM_BLACK)

	def terminate(self):
		super(VisionEnhancementProvider, self).terminate()
		Magnification.MagUninitialize()

	def registerEventExtensionPoints(self, extensionPoints):
		# The screen curtain isn't interested in any events
		pass

class WarnOnLoadDialog(gui.nvdaControls.MessageDialog):

	def _addContents(self, contentsSizer):
		showWarningOnLoadText = _("Always &show this warning when loading {description}").format(
			description=VisionEnhancementProvider.description
		)
		self.showWarningOnLoadCheckBox = contentsSizer.addItem(wx.CheckBox(self, label=showWarningOnLoadText))
		self.showWarningOnLoadCheckBox.SetValue(
			config.conf[VisionEnhancementProvider._configSection][VisionEnhancementProvider.name][
				"warnOnLoad"
			]
		)

	def _addButtons(self, buttonHelper):
		yesButton = buttonHelper.addButton(
			self,
			id=wx.ID_YES,
			# Translators: A button in the screen curtain warning dialog which allows the user to
			# agree to enabling the curtain.
			label=_("&Yes")
		)
		yesButton.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.YES))

		noButton = buttonHelper.addButton(
			self,
			id=wx.ID_NO,
			# Translators: A button in the screen curtain warning dialog which allows the user to
			# disagree to enabling the curtain.
			label=_("&No")
		)
		noButton.SetDefault()
		noButton.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.NO))
		noButton.SetFocus()
