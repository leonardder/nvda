#visionEnhancementProviders/NVDAHighlighter.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2018-2019 NV Access Limited, Babbage B.V., Takuya Nishimoto

"""Default highlighter based on GDI Plus."""

import vision
from vision.constants import Role, Context
from vision.util import getContextRect
from windowUtils import CustomWindow
import wx
import gui
import api
from ctypes import pointer, byref, WinError
from ctypes.wintypes import COLORREF, MSG
import winUser
from logHandler import log
from mouseHandler import getTotalWidthAndHeightAndMinimumPosition
from locationHelper import RectLTWH
from collections import namedtuple
import threading
import winGDI
import weakref
from colors import RGB
import core
import driverHandler
from gui.settingsDialogs import SettingsPanel

class HighlightStyle(
	namedtuple("HighlightStyle", ("color", "width", "style", "margin"))
):
	"""Represents the style of a highlight for a particular context.
	@ivar color: The color to use for the style
	@type color: L{RGB}
	@ivar width: The width of the lines to be drawn, in pixels.
		A higher width reduces the inner dimensions of the rectangle.
		Therefore, if you need to increase the outer dimensions of the rectangle, you need to increase the margin as well.
	@type width: int
	@ivar style: The style of the lines to be drawn;
		One of the C{winGDI.DashStyle*} enumeration constants.
	@type style: int
	@ivar margin: The number of pixels between the highlight's rectangle
		and the rectangle of the object to be highlighted.
		A higher margin stretches the highlight's rectangle.
		This value may also be negative.
	@type margin: int
	"""

BLUE = RGB(0x03, 0x36, 0xFF)
PINK = RGB(0xFF, 0x02, 0x66)
YELLOW = RGB(0xFF, 0xDE, 0x03)
DASH_BLUE =  HighlightStyle(BLUE, 5, winGDI.DashStyleDash, 5)
SOLID_PINK = HighlightStyle(PINK, 5, winGDI.DashStyleSolid, 5)
SOLID_BLUE = HighlightStyle(BLUE, 5, winGDI.DashStyleSolid, 5)
SOLID_YELLOW = HighlightStyle(YELLOW, 2, winGDI.DashStyleSolid, 2)

class VisionEnhancementProvider(vision.providerBase.VisionEnhancementProvider):
	name = "NVDAHighlighter"
	# Translators: Description for NVDA's built-in screen highlighter.
	description = _("NVDA Highlighter")
	supportedRoles = frozenset([Role.HIGHLIGHTER])
	supportedContexts = (Context.FOCUS, Context.NAVIGATOR, Context.BROWSEMODE)
	_ContextStyles = {
		Context.FOCUS: DASH_BLUE,
		Context.NAVIGATOR: SOLID_PINK,
		Context.FOCUS_NAVIGATOR: SOLID_BLUE,
		Context.BROWSEMODE: SOLID_YELLOW,
	}
	refreshInterval = 100

	# Default settings for parameters
	highlightFocus = True
	highlightNavigator = True
	highlightBrowseMode = True

	_contextOptionLabelsWithAccelerators = {
		# Translators: shown for a highlighter setting that toggles
		# highlighting the system focus.
		Context.FOCUS: _("Highlight system fo&cus"),
		# Translators: shown for a highlighter setting that toggles
		# highlighting the browse mode cursor.
		Context.BROWSEMODE: _("Highlight browse &mode cursor"),
		# Translators: shown for a highlighter setting that toggles
		# highlighting the navigator object.
		Context.NAVIGATOR: _("Highlight navigator &object"),
	}

	@classmethod
	def check(cls):
		return True

	def registerEventExtensionPoints(self, extensionPoints):
		extensionPoints.post_focusChange.register(self.handleFocusChange)
		extensionPoints.post_reviewMove.register(self.handleReviewMove)
		extensionPoints.post_browseModeMove.register(self.handleBrowseModeMove)

	def __init__(self):
		super(VisionEnhancementProvider, self).__init__()
		self.contextToRectMap = {}
		winGDI.gdiPlusInitialize()
		self.window = None
		self._highlighterThread = threading.Thread(target=self._run)
		self._highlighterThread.daemon = True
		self._highlighterThread.start()

	def terminate(self):
		if self._highlighterThread:
			if not winUser.user32.PostThreadMessageW(self._highlighterThread.ident, winUser.WM_QUIT, 0, 0):
				raise WinError()
			# Joining the thread here somehow stops the quit message from arriving.
			#self._highlighterThread.join()
			self._highlighterThread = None
		winGDI.gdiPlusTerminate()
		self.contextToRectMap.clear()
		super(VisionEnhancementProvider, self).terminate()

	def _run(self):
		if vision._isDebug():
			log.debug("Starting NVDAHighlighter thread")
		window = self.window = HighlightWindow(self)
		self.timer = winUser.WinTimer(window.handle, 0, self.refreshInterval, None)
		msg = MSG()
		while winUser.getMessage(byref(msg), None, 0, 0):
			winUser.user32.TranslateMessage(byref(msg))
			winUser.user32.DispatchMessageW(byref(msg))
		if vision._isDebug():
			log.debug("Quit message received on NVDAHighlighter thread")
		if self.timer:
			self.timer.terminate()
			self.timer = None
		if self.window:
			self.window.destroy()
			self.window = None

	def _get_supportedSettings(self):
		settings = []
		for context in self.supportedContexts:
			settings.append(driverHandler.BooleanDriverSetting(
				'highlight%s' % (context[0].upper() + context[1:]),
				self._contextOptionLabelsWithAccelerators[context],
				defaultVal=True
			))
		return settings

	def updateContextRect(self, context, rect=None, obj=None):
		"""Updates the position rectangle of the highlight for the specified context.
		If rect is specified, the method directly writes the rectangle to the contextToRectMap.
		Otherwise, it will call L{getContextRect}
		"""
		if context not in self.enabledContexts:
			return
		if rect is None:
			try:
				rect= getContextRect(context, obj=obj)
			except (LookupError, NotImplementedError, RuntimeError):
				rect = None
		self.contextToRectMap[context] = rect

	def handleFocusChange(self, obj):
		self.updateContextRect(context=Context.FOCUS, obj=obj)
		if not api.isObjectInActiveTreeInterceptor(obj):
			self.contextToRectMap.pop(Context.BROWSEMODE, None)
		else:
			self.handleBrowseModeMove()

	def handleReviewMove(self, context):
		if context in (Context.NAVIGATOR, Context.REVIEW):
			self.updateContextRect(context=Context.NAVIGATOR)

	def handleBrowseModeMove(self):
		self.updateContextRect(context=Context.BROWSEMODE)

	def refresh(self):
		"""Refreshes the screen positions of the enabled highlights.
		"""
		if self.window:
			self.window.refresh()

	def _get_enabledContexts(self):
		"""Gets the contexts for which the highlighter is enabled.
		"""
		return tuple(
			context for context in self.supportedContexts
			if getattr(self, 'highlight%s' % (context[0].upper() + context[1:]))
		)

class HighlightWindow(CustomWindow):
	transparency = 0xff
	className = u"NVDAHighlighter"
	windowName = u"NVDA Highlighter Window"
	windowStyle = winUser.WS_POPUP | winUser.WS_DISABLED
	extendedWindowStyle = winUser.WS_EX_TOPMOST | winUser.WS_EX_LAYERED

	@classmethod
	def _get__wClass(cls):
		wClass = super(HighlightWindow, cls)._wClass
		wClass.style = winUser.CS_HREDRAW | winUser.CS_VREDRAW
		return wClass

	def updateLocationForDisplays(self):
		if vision._isDebug():
			log.debug("Updating NVDAHighlighter window location for displays")
		displays = [ wx.Display(i).GetGeometry() for i in range(wx.Display.GetCount()) ]
		screenWidth, screenHeight, minPos = getTotalWidthAndHeightAndMinimumPosition(displays)
		# Hack: Windows has a "feature" that will stop desktop shortcut hotkeys from working when a window is full screen.
		# Removing one line of pixels from the bottom of the screen will fix this.
		left = minPos.x
		top = minPos.y
		width = screenWidth
		height = screenHeight-1
		self.location = RectLTWH(left, top, width, height)
		winUser.user32.ShowWindow(self.handle, winUser.SW_HIDE)
		if not winUser.user32.SetWindowPos(
			self.handle,
			winUser.HWND_TOPMOST,
			left, top, width, height,
			winUser.SWP_NOACTIVATE
		):
			raise WinError()
		winUser.user32.ShowWindow(self.handle, winUser.SW_SHOWNA)

	def __init__(self, highlighter):
		if vision._isDebug():
			log.debug("initializing NVDAHighlighter window")
		super(HighlightWindow, self).__init__(
			windowName=self.windowName,
			windowStyle=self.windowStyle,
			extendedWindowStyle=self.extendedWindowStyle,
			parent=gui.mainFrame.Handle
		)
		self.location = None
		self.highlighterRef = weakref.ref(highlighter)
		self.transparentBrush = winGDI.gdi32.CreateSolidBrush(COLORREF(0))
		winUser.SetLayeredWindowAttributes(self.handle, None, self.transparency, winUser.LWA_ALPHA | winUser.LWA_COLORKEY)
		self.updateLocationForDisplays()
		if not winUser.user32.UpdateWindow(self.handle):
			raise WinError()

	def windowProc(self, hwnd, msg, wParam, lParam):
		if msg == winUser.WM_PAINT:
			self._paint()
			# Ensure the window is top most
			winUser.user32.SetWindowPos(
				self.handle,
				winUser.HWND_TOPMOST,
				0, 0, 0, 0,
				winUser.SWP_NOACTIVATE | winUser.SWP_NOMOVE | winUser.SWP_NOSIZE
			)
		elif msg == winUser.WM_DESTROY:
			winUser.user32.PostQuitMessage(0)
		elif msg == winUser.WM_TIMER:
			self.refresh()
		elif msg == winUser.WM_DISPLAYCHANGE:
			# wx might not be aware of the display change at this point
			core.callLater(100, self.updateLocationForDisplays)

	def _paint(self):
		highlighter = self.highlighterRef()
		if not highlighter:
			# The highlighter instance died unexpectedly, kill the window as well
			winUser.user32.PostQuitMessage(0)
			return
		contextRects = {}
		for context in highlighter.enabledContexts:
			rect = highlighter.contextToRectMap.get(context)
			if not rect:
				continue
			elif context == Context.NAVIGATOR and contextRects.get(Context.FOCUS) == rect:
				# When the focus overlaps the navigator object, which is usually the case,
				# show a different highlight style.
				# Focus is in contextRects, do not show the standalone focus highlight.
				contextRects.pop(Context.FOCUS)
				# Navigator object might be in contextRects as well
				contextRects.pop(Context.NAVIGATOR, None)
				context = Context.FOCUS_NAVIGATOR
			contextRects[context] = rect
		if not contextRects:
			return
		windowRect = winUser.getClientRect(self.handle)
		with winUser.paint(self.handle) as hdc:
			winUser.user32.FillRect(hdc, byref(windowRect), self.transparentBrush)
			with winGDI.GDIPlusGraphicsContext(hdc) as graphicsContext:
				for context, rect in contextRects.items():
					HighlightStyle = highlighter._ContextStyles[context]
					# Before calculating logical coordinates,
					# make sure the rectangle falls within the highlighter window
					rect = rect.intersection(self.location)
					try:
						rect = rect.toLogical(self.handle)
					except RuntimeError:
						log.debugWarning("", exc_info=True)
					rect = rect.toClient(self.handle)
					try:
						rect = rect.expandOrShrink(HighlightStyle.margin)
					except RuntimeError:
						pass
					with winGDI.GDIPlusPen(
						HighlightStyle.color.toGDIPlusARGB(),
						HighlightStyle.width,
						HighlightStyle.style
					) as pen:
						winGDI.gdiPlusDrawRectangle(graphicsContext, pen, *rect.toLTWH())

	def refresh(self):
		winUser.user32.InvalidateRect(self.handle, None, True)

class NVDAHighlighterSettingsPanel(SettingsPanel):

	def makeSettings(self, sizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=sizer)
		# Translators: This is the label for a checkbox in the
		# default highlighter settings panel to enable highlighting the focus.
		self.highlightFocusCheckBox=sHelper.addItem(wx.CheckBox(self,label=_("Highlight &focus")))
		self.highlightFocusCheckBox.SetValue(config.conf['vision'][VisionEnhancementProvider.name]["highlightFocus"])
		# Translators: This is the label for a checkbox in the
		# default highlighter settings panel to enable highlighting the navigator object.
		self.highlightNavigatorObjCheckBox=sHelper.addItem(wx.CheckBox(self,label=_("Highlight &navigator object")))
		self.highlightNavigatorObjCheckBox.SetValue(config.conf['vision'][VisionEnhancementProvider.name]["highlightNavigatorObj"])
		# Translators: This is the label for a checkbox in the
		# default highlighter settings panel to enable highlighting the virtual caret (such as in browse mode).
		self.highlightBrowseModeCheckBox=sHelper.addItem(wx.CheckBox(self,label=_("Follow &browse mode caret")))
		self.highlightBrowseModeCheckBox.SetValue(config.conf['vision'][VisionEnhancementProvider.name]["highlightBrowseMode"])

	def onSave(self):
		config.conf['vision'][VisionEnhancementProvider.name]["highlightFocus"]=self.highlightFocusCheckBox.IsChecked()
		config.conf['vision'][VisionEnhancementProvider.name]["highlightNavigatorObj"]=self.highlightNavigatorObjCheckBox.IsChecked()
		config.conf['vision'][VisionEnhancementProvider.name]["highlightBrowseMode"]=self.highlightBrowseModeCheckBox.IsChecked()

VisionEnhancementProvider.guiPanelCls = NVDAHighlighterSettingsPanel
