#visionEnhancementProviders/NVDAHighlighter.py
#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2018-2019 NV Access Limited, Babbage B.V., Takuya Nishimoto

"""Default highlighter based on GDI Plus."""

from vision import Highlighter, CONTEXT_FOCUS, CONTEXT_NAVIGATOR, CONTEXT_CARET, _isDebug
from windowUtils import CustomWindow
import wx
import gui
import api
from ctypes import pointer, byref, WinError
from ctypes.wintypes import COLORREF, MSG
import winUser
from logHandler import log
from mouseHandler import getTotalWidthAndHeightAndMinimumPosition
import cursorManager
from locationHelper import RectLTRB, RectLTWH
import config
from collections import namedtuple
import threading
import winGDI
import weakref
from colors import RGB
import core

# Highlighter specific contexts
#: Context for overlapping focus and navigator objects
CONTEXT_FOCUS_NAVIGATOR = "focusNavigatorOverlap"

class HighlightStyle(
	namedtuple("HighlightStyle", ("color", "width", "style", "margin"))
):
	"""Represents the style of a highlight for a particular context.
	@ivar color: THe color to use for the style
	@type color: L{RGB}
	@ivar width: The width of the lines to be drawn, in pixels.
		A higher width reduces the inner dimentions of the rectangle.
		Therefore, if you need to increase the outer dimentions of the rectangle, you need to increase the margin as well.
	@type width: int
	@ivar style: The style of the lines to be drawn;
		One of the C{winGDI.DashStyle*} enumeration constants.
	@type style: int
	@ivar margin: The number of pixels between the highlight's rectangle
		and the rectangle of the object to be highlighted.
		A higher margin increases both the inner and outer dimentions of the highlight's rectangle.
		This value may also be negative.
	@type margin: int
	"""
	__slots__ = ()

class VisionEnhancementProvider(Highlighter):
	name = "NVDAHighlighter"
	# Translators: Description for NVDA's built-in screen highlighter.
	description = _("NVDA Highlighter")
	supportedHighlightContexts = (CONTEXT_FOCUS, CONTEXT_NAVIGATOR, CONTEXT_CARET)
	customHighlightContexts = (CONTEXT_FOCUS_NAVIGATOR,)
	_ContextStyles = {
		CONTEXT_FOCUS: HighlightStyle(RGB(0x03, 0x36, 0xff), 5, winGDI.DashStyleDash, 5),
		CONTEXT_NAVIGATOR: HighlightStyle(RGB(0xff, 0x02, 0x66), 5, winGDI.DashStyleSolid, 5),
		CONTEXT_FOCUS_NAVIGATOR: HighlightStyle(RGB(0x03, 0x36, 0xff), 5, winGDI.DashStyleSolid, 5),
		CONTEXT_CARET: HighlightStyle(RGB(0xff, 0xde, 0x03), 2, winGDI.DashStyleSolid, 2),
	}
	refreshInterval = 100

	def initializeHighlighter(self):
		super(VisionEnhancementProvider, self).initializeHighlighter()
		winGDI.gdiPlusInitialize()
		self.windows = {}
		self.transparentBrush = winGDI.gdi32.CreateSolidBrush(COLORREF(0))
		self._highlighterThread = threading.Thread(target=self._run)
		self._highlighterThread.daemon = True
		self._highlighterThread.start()

	def terminateHighlighter(self):
		if self._highlighterThread:
			if not winUser.user32.PostThreadMessageW(self._highlighterThread.ident, winUser.WM_QUIT, 0, 0):
				raise WinError()
			self._highlighterThread.join()
			self._highlighterThread = None
		winGDI.gdiPlusTerminate()
		super(VisionEnhancementProvider, self).terminateHighlighter()

	def _run(self):
		if _isDebug():
			log.debug("Starting NVDAHighlighter thread")
		for context in self.supportedHighlightContexts + self.customHighlightContexts:
			self.windows[context] = highlightWindowFactory(context)(self)
		timer = 	winUser.user32.SetTimer(0, 0, self.refreshInterval, None)
		msg = MSG()
		while winUser.getMessage(byref(msg),None,0,0) != 0:
			# Avoid using a timer
			if msg.message == winUser.WM_TIMER:
				self.refresh()
				continue
			winUser.user32.TranslateMessage(byref(msg))
			winUser.user32.DispatchMessageW(byref(msg))
		if _isDebug():
			log.debug("Quit message received on NVDAHighlighter thread")
		if not winUser.user32.KillTimer(0, timer):
			raise WinError()
		for window in self.windows.values():
			window.destroy()
		self.windows.clear()

	def refresh(self):
		contextRects = {}
		for context in self.enabledHighlightContexts:
			rect = self.contextToRectMap.get(context)
			if not rect:
				continue
			if context == CONTEXT_CARET and not isinstance(api.getCaretObject(), cursorManager.CursorManager):
				# Non virtual carets are currently not supported.
				# As they are physical, they are visible by themselves.
				continue
			elif context == CONTEXT_NAVIGATOR and contextRects.get(CONTEXT_FOCUS) == rect:
				# When the focus overlaps the navigator object, which is usually the case,
				# show a different highlight style.
				# Focus is in contextRects, do not show the standalone focus highlight.
				contextRects.pop(CONTEXT_FOCUS)
				# Navigator object might be in contextRects as well
				contextRects.pop(CONTEXT_NAVIGATOR, None)
				context = CONTEXT_FOCUS_NAVIGATOR
			contextRects[context] = rect
		windowContexts = set(self.windows.keys())
		showWindowContexts = set(contextRects)
		for context in windowContexts:
			window = self.windows[context]
			if context in showWindowContexts:
				window.move(contextRects[context])
				window.show()
				#window.refresh()
			else:
				window.show(False)

class HighlightWindow(CustomWindow):
	transparency = 0xff
	windowStyle = winUser.WS_POPUP | winUser.WS_DISABLED
	extendedWindowStyle = winUser.WS_EX_TOPMOST | winUser.WS_EX_LAYERED

	@classmethod
	def _get__wClass(cls):
		wClass = super(HighlightWindow, cls)._wClass
		wClass.style = winUser.CS_HREDRAW | winUser.CS_VREDRAW
		return wClass

	def _get_visible(self):
		return winUser.isWindowVisible(self.handle)

	def show(self, show=True):
		if show is self.visible:
			return
		winUser.user32.ShowWindow(self.handle, winUser.SW_HIDE if not show else winUser.SW_SHOWNA)

	def move(self, rect):
		highlighter = self.highlighterRef()
		if not highlighter:
			raise RuntimeError("Highlight window exists while highlighter died")
		HighlightStyle = highlighter._ContextStyles[self.context]
		rect = rect.expandOrShrink(HighlightStyle.margin)
		self.location = rect
		if not winUser.user32.SetWindowPos(
			self.handle,
			winUser.HWND_TOPMOST,
			rect.left, rect.top, rect.width, rect.height,
			winUser.SWP_NOACTIVATE
		):
			raise WinError()

	def __init__(self, highlighter):
		if _isDebug():
			log.debug("initializing %s" % self.__class__.__name__)
		super(HighlightWindow, self).__init__(
			windowName=u"NVDA Highlighter %s window" % self.context,
			windowStyle=self.windowStyle,
			extendedWindowStyle=self.extendedWindowStyle,
			parent=gui.mainFrame.Handle
		)
		self.location = RectLTRB(0, 0, 0, 0)
		self.highlighterRef = weakref.ref(highlighter)
		winUser.SetLayeredWindowAttributes(self.handle, None, self.transparency, winUser.LWA_ALPHA | winUser.LWA_COLORKEY)
		if not winUser.user32.UpdateWindow(self.handle):
			raise WinError()

	def windowProc(self, hwnd, msg, wParam, lParam):
		if msg == winUser.WM_PAINT:
			self._paint()


	def _paint(self):
		highlighter = self.highlighterRef()
		if not highlighter:
			# The highlighter instance died unexpectedly, kill the window as well
			winUser.user32.PostQuitMessage(0)
			return
		windowRect = winUser.getClientRect(self.handle)
		with winUser.paint(self.handle) as hdc:
			winUser.user32.FillRect(hdc, byref(windowRect), highlighter.transparentBrush)
			with winGDI.GDIPlusGraphicsContext(hdc) as graphicsContext:
				HighlightStyle = highlighter._ContextStyles[self.context]
				with winGDI.GDIPlusPen(
					HighlightStyle.color.toGDIPlusARGB(),
					HighlightStyle.width,
					HighlightStyle.style
				) as pen:
					winGDI.gdiPlusDrawRectangle(graphicsContext, pen, *RectLTWH.fromCompatibleType(windowRect))

	def refresh(self):
		winUser.user32.InvalidateRect(self.handle, None, True)

def highlightWindowFactory(context):
	contextTitle = context[0].upper()+context[1:]
	return type("{context}HighlightWindow".format(context=contextTitle), (HighlightWindow,), {
		"context": context,
		"className": u"NVDA{context}Highlighter".format(context=contextTitle)
	})
