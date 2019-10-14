# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2010-2019 NV Access Limited, Soronel Haetir, Babbage B.V.

import ctypes
import objbase
from comtypes import IUnknown, IServiceProvider , GUID, COMMETHOD, HRESULT, BSTR
from ctypes import POINTER, c_int, c_short, c_ushort, c_ulong
import comtypes.client.dynamic
from comtypes.automation import IDispatch
from locationHelper import RectLTWH
from logHandler import log
import textInfos.offsets

from NVDAObjects.behaviors import EditableTextWithoutAutoSelectDetection
from NVDAObjects.window import Window

from NVDAObjects.window import DisplayModelEditableText
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.UIA import UIA

import appModuleHandler
import controlTypes
import fnmatch


#
# A few helpful constants
#

SVsTextManager = GUID('{F5E7E71D-1401-11D1-883B-0000F87579D2}')
VsVersion_None = 0
VsVersion_2002 = 1
VsVersion_2003 = 2
VsVersion_2005 = 3
VsVersion_2008 = 4

# Possible values of the VS .Type property of VS windows.
# According to the docs this property should not be used but I have not been able to determine all of the needed values
# of the .Kind property which is the suggested alternative.
#
# I don't have a type library or header defining the VsWindowType enumeration so only .Type values
#		I've actually encountered are defined.
# Known missing values are:
#	CodeWindow, Designer, Browser, Watch, Locals,
#	SolutionExplorer, Properties, Find, FindReplace, Toolbox, LinkedWindowFrame, MainWindow, Preview,
#	ColorPalettte, ToolWindowTaskList, Autos, CallStack, Threads, DocumentOutline, RunningDocuments
# Most of these host controls which should hopefully be the "real" window by the time any text needs to be rendered.
VsWindowTypeCommand = 15
VsWindowTypeDocument = 16
VsWindowTypeOutput = 17

# Scroll bar selector
SB_HORZ = 0
SB_VERT = 1


class AppModule(appModuleHandler.AppModule):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		vsMajor, vsMinor, rest = self.productVersion.split(".", 2)
		self.vsMajor, self.vsMinor = int(vsMajor), int(vsMinor)

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Only use this overlay class if the top level automation object for the IDE can be retrieved,
		# as it will not work otherwise.
		if self.DTE and (
			obj.windowClassName == "VsTextEditPane" or (
				isinstance(obj, UIA) and obj.UIAElement.CachedClassName == "WpfTextView"
			)
		):
			try:
				clsList.remove(DisplayModelEditableText)
			except ValueError:
				pass
			clsList.insert(0, VsTextEditPane)

		elif (
			(self.vsMajor == 15 and self.vsMinor >= 3)
			or self.vsMajor >= 16
		):
			if obj.role == controlTypes.ROLE_TREEVIEWITEM and obj.windowClassName == "LiteTreeView32":
				clsList.insert(0, ObjectsTreeItem)

	def _get_DTE(self):
		# Return the already fetched instance if there is one.
		try:
			if self._DTE:
				return self._DTE
		except AttributeError:
			pass

		# Retrieve and cache the top level automation object for the IDE
		try:
			self._DTE = comtypes.client.GetActiveObject(f"VisualStudio.DTE.{self.vsMajor}.0", dynamic=True)
		except comtypes.COMError:
			# None found.
			log.debugWarning("No top level automation object found", exc_info=True)
			self._DTE = None
		return self._DTE

	def _get_textManager(self):
		try:
			if self._textManager:
				return self._textManager
		except AttributeError:
			pass

		serviceProvider = self.DTE.QueryInterface(comtypes.IServiceProvider)
		self._textManager = serviceProvider.QueryService(SVsTextManager, IVsTextManager)
		return self._textManager

class VsTextEditPaneTextInfo(textInfos.offsets.OffsetsTextInfo):

	def _get__selectionObject(self):
		selection = None
		if self._window.Kind == "Document":
			selection = self._window.Selection
		else:
			selection = self._window.Object.ActivePane.TextDocument.Selection
		self._selectionObject = selection 
		return selection

	def _createEditPoint(self):
		return self._selectionObject.ActivePoint.CreateEditPoint()

	def _get_lineHeight(self):
		self.lineHeight = self._textView.GetLineHeight()
		return self.lineHeight

	def _getOffsetFromPoint(self,x,y):
		yMinUnit, yMaxUnit, yVisible, yFirstVisible = self._textView.GetScrollInfo(SB_VERT)
		hMinUnit, hMaxUnit, hVisible, hFirstVisible = self._textView.GetScrollInfo(SB_HORZ)
		# These should probably be cached as they are fairly unlikely to change, but ...
		charWidth = self._window.Width // hVisible

		offsetLine = (y - self._window.Top) // self.lineHeight + yFirstVisible
		offsetChar = (x - self._window.Left) // charWidth + hFirstVisible
		return self._textView.GetNearestPosition(offsetLine, offsetChar)[0]

	def __init__(self, obj, position):
		self._window = obj._window
		self._textView = obj._textView
		super().__init__(obj, position)

	def _getCaretOffset(self):
		return self._createEditPoint().AbsoluteCharOffset - 1

	def _setCaretOffset(self, offset):
		self._selectionObject.MoveToAbsoluteOffset(offset + 1)

	def _setSelectionOffsets(self, start, end):
		self._selectionObject.MoveToAbsoluteOffset(start + 1)
		self._selectionObject.MoveToAbsoluteOffset(end + 1, True)

	def _getSelectionOffsets(self):
		startPos = self._selectionObject.ActivePoint.CreateEditPoint().AbsoluteCharOffset
		endPos = self._selectionObject.AnchorPoint.CreateEditPoint().AbsoluteCharOffset
		return (startPos -1, endPos -1)

	def _getTextRange(self, start, end):
		editPointStart = self._createEditPoint()
		editPointStart.StartOfDocument()
		if start > 0:
			editPointStart.MoveToAbsoluteOffset(start + 1)
		return editPointStart.GetText(end - start)

	def _getCharacterOffsets(self, offset):
		editPointStart = self._createEditPoint()
		editPointStart.MoveToAbsoluteOffset(offset + 1)
		editPointStart.CharLeft()
		editPointEnd = editPointStart.CreateEditPoint()
		editPointEnd.CharRight()
		return (editPointStart.AbsoluteCharOffset -1, editPointEnd.AbsoluteCharOffset -1)

	def _getWordOffsets(self, offset):
		editPointStart = self._createEditPoint()
		editPointStart.MoveToAbsoluteOffset(offset + 1)
		editPointStart.WordLeft()
		editPointEnd = editPointStart.CreateEditPoint()
		editPointEnd.WordRight()
		return (editPointStart.AbsoluteCharOffset -1, editPointEnd.AbsoluteCharOffset -1)

	def _getLineOffsets(self, offset):
		editPointStart = self._createEditPoint()
		editPointStart.MoveToAbsoluteOffset(offset + 1)
		editPointStart.StartOfLine()
		editPointEnd = editPointStart.CreateEditPoint()
		editPointEnd.EndOfLine()
		return (editPointStart.AbsoluteCharOffset -1, editPointEnd.AbsoluteCharOffset -1)

	def _getLineNumFromOffset(self, offset):
		editPoint = self._createEditPoint()
		editPoint.MoveToAbsoluteOffset(offset + 1)
		return editPoint.Line

	def _getStoryLength(self):
		editPoint = self._createEditPoint()
		editPoint.EndOfDocument()
		return editPoint.AbsoluteCharOffset


class VsTextEditPane(EditableTextWithoutAutoSelectDetection, Window):
	TextInfo = VsTextEditPaneTextInfo

	def initOverlayClass(self):
		self._window = self.appModule.DTE.ActiveWindow
		self.location = RectLTWH(
			self._window.Left,
			self._window.Top,
			self._window.Width,
			self._window.Height
		)
		self._textView = self.appModule.textManager.GetActiveView(True, None)

	def event_valueChange(self):
		pass

class IVsTextView(IUnknown):
	_case_insensitive_ = True
	_iid_ = GUID('{BB23A14B-7C61-469A-9890-A95648CED5E6}')
	_idlflags_ = []


class IVsTextManager(comtypes.IUnknown):
	_case_insensitive_ = True
	_iid_ = GUID('{909F83E3-B3FC-4BBF-8820-64378744B39B}')
	_idlflags_ = []

IVsTextManager._methods_ = [
	COMMETHOD([], HRESULT, 'RegisterView',
		( ['in'], POINTER(IVsTextView), 'pView' ),
		( ['in'], POINTER(IUnknown), 'pBuffer' )),
	COMMETHOD([], HRESULT, 'UnregisterView',
		( ['in'], POINTER(IVsTextView), 'pView' )),
	COMMETHOD([], HRESULT, 'EnumViews',
		( ['in'], POINTER(IUnknown), 'pBuffer' ),
		( ['out'], POINTER(POINTER(IUnknown)), 'ppEnum' )),
    COMMETHOD([], HRESULT, 'CreateSelectionAction',
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppAction' )),
    COMMETHOD([], HRESULT, 'MapFilenameToLanguageSID',
              ( ['in'], POINTER(c_ushort), 'pszFileName' ),
              ( ['out'], POINTER(GUID), 'pguidLangSID' )),
    COMMETHOD([], HRESULT, 'GetRegisteredMarkerTypeID',
              ( ['in'], POINTER(GUID), 'pguidMarker' ),
              ( ['out'], POINTER(c_int), 'piMarkerTypeID' )),
    COMMETHOD([], HRESULT, 'GetMarkerTypeInterface',
              ( ['in'], c_int, 'iMarkerTypeID' ),
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppMarkerType' )),
    COMMETHOD([], HRESULT, 'GetMarkerTypeCount',
              ( ['out'], POINTER(c_int), 'piMarkerTypeCount' )),
    COMMETHOD([], HRESULT, 'GetActiveView',
              ( ['in'], c_int, 'fMustHaveFocus' ),
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['out'], POINTER(POINTER(IVsTextView)), 'ppView' )),
    COMMETHOD([], HRESULT, 'GetUserPreferences',
              ( ['out'], POINTER(c_int), 'pViewPrefs' ),
              ( ['out'], POINTER(c_int), 'pFramePrefs' ),
              ( ['in', 'out'], POINTER(c_int), 'pLangPrefs' ),
              ( ['in', 'out'], POINTER(c_int), 'pColorPrefs' )),
    COMMETHOD([], HRESULT, 'SetUserPreferences',
              ( ['in'], POINTER(c_int), 'pViewPrefs' ),
              ( ['in'], POINTER(c_int), 'pFramePrefs' ),
              ( ['in'], POINTER(c_int), 'pLangPrefs' ),
              ( ['in'], POINTER(c_int), 'pColorPrefs' )),
    COMMETHOD([], HRESULT, 'SetFileChangeAdvise',
              ( ['in'], POINTER(c_ushort), 'pszFileName' ),
              ( ['in'], c_int, 'fStart' )),
    COMMETHOD([], HRESULT, 'SuspendFileChangeAdvise',
              ( ['in'], POINTER(c_ushort), 'pszFileName' ),
              ( ['in'], c_int, 'fSuspend' )),
    COMMETHOD([], HRESULT, 'NavigateToPosition',
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['in'], POINTER(GUID), 'guidDocViewType' ),
              ( ['in'], c_int, 'iPos' ),
              ( ['in'], c_int, 'iLen' )),
    COMMETHOD([], HRESULT, 'NavigateToLineAndColumn',
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['in'], POINTER(GUID), 'guidDocViewType' ),
              ( ['in'], c_int, 'iStartRow' ),
              ( ['in'], c_int, 'iStartIndex' ),
              ( ['in'], c_int, 'iEndRow' ),
              ( ['in'], c_int, 'iEndIndex' )),
    COMMETHOD([], HRESULT, 'GetBufferSccStatus',
              ( ['in'], POINTER(IUnknown), 'pBufData' ),
              ( ['out'], POINTER(c_int), 'pbNonEditable' )),
    COMMETHOD([], HRESULT, 'RegisterBuffer',
              ( ['in'], POINTER(IUnknown), 'pBuffer' )),
    COMMETHOD([], HRESULT, 'UnregisterBuffer',
              ( ['in'], POINTER(IUnknown), 'pBuffer' )),
    COMMETHOD([], HRESULT, 'EnumBuffers',
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppEnum' )),
    COMMETHOD([], HRESULT, 'GetPerLanguagePreferences',
              ( ['out'], POINTER(c_int), 'pLangPrefs' )),
    COMMETHOD([], HRESULT, 'SetPerLanguagePreferences',
              ( ['in'], POINTER(c_int), 'pLangPrefs' )),
    COMMETHOD([], HRESULT, 'AttemptToCheckOutBufferFromScc',
              ( ['in'], POINTER(IUnknown), 'pBufData' ),
              ( ['out'], POINTER(c_int), 'pfCheckoutSucceeded' )),
    COMMETHOD([], HRESULT, 'GetShortcutManager',
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppShortcutMgr' )),
    COMMETHOD([], HRESULT, 'RegisterIndependentView',
              ( ['in'], POINTER(IUnknown), 'punk' ),
              ( ['in'], POINTER(IUnknown), 'pBuffer' )),
    COMMETHOD([], HRESULT, 'UnregisterIndependentView',
              ( ['in'], POINTER(IUnknown), 'punk' ),
              ( ['in'], POINTER(IUnknown), 'pBuffer' )),
    COMMETHOD([], HRESULT, 'IgnoreNextFileChange',
              ( ['in'], POINTER(IUnknown), 'pBuffer' )),
    COMMETHOD([], HRESULT, 'AdjustFileChangeIgnoreCount',
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['in'], c_int, 'fIgnore' )),
    COMMETHOD([], HRESULT, 'GetBufferSccStatus2',
              ( ['in'], POINTER(c_ushort), 'pszFileName' ),
              ( ['out'], POINTER(c_int), 'pbNonEditable' ),
              ( ['out'], POINTER(c_int), 'piStatusFlags' )),
    COMMETHOD([], HRESULT, 'AttemptToCheckOutBufferFromScc2',
              ( ['in'], POINTER(c_ushort), 'pszFileName' ),
              ( ['out'], POINTER(c_int), 'pfCheckoutSucceeded' ),
              ( ['out'], POINTER(c_int), 'piStatusFlags' )),
    COMMETHOD([], HRESULT, 'EnumLanguageServices',
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppEnum' )),
    COMMETHOD([], HRESULT, 'EnumIndependentViews',
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppEnum' )),
]


IVsTextView._methods_ = [
    COMMETHOD([], HRESULT, 'Initialize',
              ( ['in'], POINTER(IUnknown), 'pBuffer' ),
              ( ['in'], comtypes.wireHWND, 'hwndParent' ),
              ( ['in'], c_ulong, 'InitFlags' ),
              ( ['in'], POINTER(c_int), 'pInitView' )),
    COMMETHOD([], HRESULT, 'CloseView'),
    COMMETHOD([], HRESULT, 'GetCaretPos',
              ( ['out'], POINTER(c_int), 'piLine' ),
              ( ['out'], POINTER(c_int), 'piColumn' )),
    COMMETHOD([], HRESULT, 'SetCaretPos',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'iColumn' )),
    COMMETHOD([], HRESULT, 'GetSelectionSpan',
              ( ['out'], POINTER(c_int), 'pSpan' )),
    COMMETHOD([], HRESULT, 'GetSelection',
              ( ['out'], POINTER(c_int), 'piAnchorLine' ),
              ( ['out'], POINTER(c_int), 'piAnchorCol' ),
              ( ['out'], POINTER(c_int), 'piEndLine' ),
              ( ['out'], POINTER(c_int), 'piEndCol' )),
    COMMETHOD([], HRESULT, 'SetSelection',
              ( ['in'], c_int, 'iAnchorLine' ),
              ( ['in'], c_int, 'iAnchorCol' ),
              ( ['in'], c_int, 'iEndLine' ),
              ( ['in'], c_int, 'iEndCol' )),
    COMMETHOD([], c_int, 'GetSelectionMode'),
    COMMETHOD([], HRESULT, 'SetSelectionMode',
              ( ['in'], c_int, 'iSelMode' )),
    COMMETHOD([], HRESULT, 'ClearSelection',
              ( ['in'], c_int, 'fMoveToAnchor' )),
    COMMETHOD([], HRESULT, 'CenterLines',
              ( ['in'], c_int, 'iTopLine' ),
              ( ['in'], c_int, 'iCount' )),
    COMMETHOD([], HRESULT, 'GetSelectedText',
              ( ['out'], POINTER(BSTR), 'pbstrText' )),
    COMMETHOD([], HRESULT, 'GetSelectionDataObject',
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppIDataObject' )),
    COMMETHOD([], HRESULT, 'GetTextStream',
              ( ['in'], c_int, 'iTopLine' ),
              ( ['in'], c_int, 'iTopCol' ),
              ( ['in'], c_int, 'iBottomLine' ),
              ( ['in'], c_int, 'iBottomCol' ),
              ( ['out'], POINTER(BSTR), 'pbstrText' )),
    COMMETHOD([], HRESULT, 'GetBuffer',
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppBuffer' )),
    COMMETHOD([], HRESULT, 'SetBuffer',
              ( ['in'], POINTER(IUnknown), 'pBuffer' )),
    COMMETHOD([], comtypes.wireHWND, 'GetWindowHandle'),
    COMMETHOD([], HRESULT, 'GetScrollInfo',
              ( ['in'], c_int, 'iBar' ),
              ( ['out'], POINTER(c_int), 'piMinUnit' ),
              ( ['out'], POINTER(c_int), 'piMaxUnit' ),
              ( ['out'], POINTER(c_int), 'piVisibleUnits' ),
              ( ['out'], POINTER(c_int), 'piFirstVisibleUnit' )),
    COMMETHOD([], HRESULT, 'SetScrollPosition',
              ( ['in'], c_int, 'iBar' ),
              ( ['in'], c_int, 'iFirstVisibleUnit' )),
    COMMETHOD([], HRESULT, 'AddCommandFilter',
              ( ['in'], POINTER(IUnknown), 'pNewCmdTarg' ),
              ( ['out'], POINTER(POINTER(IUnknown)), 'ppNextCmdTarg' )),
    COMMETHOD([], HRESULT, 'RemoveCommandFilter',
              ( ['in'], POINTER(IUnknown), 'pCmdTarg' )),
    COMMETHOD([], HRESULT, 'UpdateCompletionStatus',
              ( ['in'], POINTER(IUnknown), 'pCompSet' ),
              ( ['in'], c_ulong, 'dwFlags' )),
    COMMETHOD([], HRESULT, 'UpdateTipWindow',
              ( ['in'], POINTER(IUnknown), 'pTipWindow' ),
              ( ['in'], c_ulong, 'dwFlags' )),
    COMMETHOD([], HRESULT, 'GetWordExtent',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'iCol' ),
              ( ['in'], c_ulong, 'dwFlags' ),
              ( ['out'], POINTER(c_int), 'pSpan' )),
    COMMETHOD([], HRESULT, 'RestrictViewRange',
              ( ['in'], c_int, 'iMinLine' ),
              ( ['in'], c_int, 'iMaxLine' ),
              ( ['in'], POINTER(IUnknown), 'pClient' )),
    COMMETHOD([], HRESULT, 'ReplaceTextOnLine',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'iStartCol' ),
              ( ['in'], c_int, 'iCharsToReplace' ),
              ( ['in'], POINTER(c_ushort), 'pszNewText' ),
              ( ['in'], c_int, 'iNewLen' )),
    COMMETHOD([], HRESULT, 'GetLineAndColumn',
              ( ['in'], c_int, 'iPos' ),
              ( ['out'], POINTER(c_int), 'piLine' ),
              ( ['out'], POINTER(c_int), 'piIndex' )),
    COMMETHOD([], HRESULT, 'GetNearestPosition',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'iCol' ),
              ( ['out'], POINTER(c_int), 'piPos' ),
              ( ['out'], POINTER(c_int), 'piVirtualSpaces' )),
    COMMETHOD([], HRESULT, 'UpdateViewFrameCaption'),
    COMMETHOD([], HRESULT, 'CenterColumns',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'iLeftCol' ),
              ( ['in'], c_int, 'iColCount' )),
    COMMETHOD([], HRESULT, 'EnsureSpanVisible',
              ( ['in'], c_int, 'span' )),
    COMMETHOD([], HRESULT, 'PositionCaretForEditing',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'cIndentLevels' )),
    COMMETHOD([], HRESULT, 'GetPointOfLineColumn',
              ( ['in'], c_int, 'iLine' ),
              ( ['in'], c_int, 'iCol' ),
              ( ['retval', 'out'], POINTER(ctypes.wintypes.tagPOINT), 'ppt' )),
    COMMETHOD([], HRESULT, 'GetLineHeight',
              ( ['retval', 'out'], POINTER(c_int), 'piLineHeight' )),
    COMMETHOD([], HRESULT, 'HighlightMatchingBrace',
              ( ['in'], c_ulong, 'dwFlags' ),
              ( ['in'], c_ulong, 'cSpans' ),
              ( ['in'], POINTER(c_int), 'rgBaseSpans' )),
    COMMETHOD([], HRESULT, 'SendExplicitFocus'),
    COMMETHOD([], HRESULT, 'SetTopLine',
              ( ['in'], c_int, 'iBaseLine' )),
]

class ObjectsTreeItem(IAccessible):

	def _get_focusRedirect(self):
		"""
		Returns the correct focused item in the object explorer trees
		"""

		if not controlTypes.STATE_FOCUSED in self.states:
			# Object explorer tree views have a bad IAccessible implementation.
			# When expanding a primary node and going to secondary node, the 
			# focus is placed to the next root node, so we need to redirect
			# it to the real focused widget. Fortunately, the states are
			# still correct and we can detect if this is really focused or not.
			return self.objectWithFocus()

	def _get_positionInfo(self):
		return {
			"level": int(self.IAccessibleObject.accValue(self.IAccessibleChildID))
		}
