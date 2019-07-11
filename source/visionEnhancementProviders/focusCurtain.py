from vision.constants import Role, Context
from .NVDAHighlighter import *
import winGDI
from colors import RGB
import winUser
from ctypes import byref

class CurtainWindow(HighlightWindow):
	transparency = 0xff
	className = u"NVDAFocusCurtain"
	windowName = u"NVDA Focus Curtain Window"
	transparentColor = 0x0
	whiteBrush = winGDI.gdi32.CreateSolidBrush(COLORREF(0xffffff))

	@classmethod
	def _get__wClass(cls):
		wClass = super(HighlightWindow, cls)._wClass
		wClass.style = winUser.CS_HREDRAW | winUser.CS_VREDRAW
		wClass.hbrBackground = cls.whiteBrush
		return wClass

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
				contextRects.pop(Context.NAVIGATOR, None)
			contextRects[context] = rect
		if not contextRects:
			return
		with winUser.paint(self.handle) as hdc:
			windowRect = winUser.getClientRect(self.handle)
			for rect in contextRects.values():
				rect = rect.intersection(self.location)
				try:
					rect = rect.toLogical(self.handle)
				except RuntimeError:
					log.debugWarning("", exc_info=True)
				rect = rect.toClient(self.handle)
				winRect = rect.toRECT()
				winUser.user32.FillRect(hdc, byref(winRect), self.transparentBrush)

class VisionEnhancementProvider(VisionEnhancementProvider):
	name = "focusCurtain"
	# Translators: Description for NVDA's built-in screen highlighter.
	description = _("Babbage Focus Curtain")
	supportedSettings = ()
	refreshInterval = 100
	customWindowClass = CurtainWindow

