# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2010-2019 NV Access Limited, Soronel Haetir, Babbage B.V.

import ctypes
import objbase
from comtypes import IUnknown, IServiceProvider , GUID, COMMETHOD, HRESULT, BSTR
import comtypes
from ctypes import POINTER, c_int, c_short, c_ushort, c_ulong
from comtypes.automation import IDispatch
from locationHelper import RectLTWH
from logHandler import log
import textInfos.offsets

from NVDAObjects.behaviors import EditableText
from NVDAObjects.window import Window

from NVDAObjects.window import DisplayModelEditableText
from NVDAObjects.IAccessible import IAccessible
from NVDAObjects.UIA import UIA

import appModuleHandler
import controlTypes

# A few helpful constants

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


class VsTextEditPaneTextInfo(textInfos.offsets.OffsetsTextInfo):

	def _get__selectionObject(self):
		if self.obj._window.Kind == "Document":
			selection = self.obj._window.Selection
		elif self.obj._window.Kind == "Tool":
			selection = self.obj._window.Object.TextDocument.Selection
		else:
			raise RuntimeError(f"Unknown window type: {self.obj._window.Kind}")
		self._selectionObject = selection 
		return selection

	def _createEditPoint(self):
		return self._selectionObject.ActivePoint.CreateEditPoint()

	def _getCaretOffset(self):
		return self._createEditPoint().AbsoluteCharOffset - 1

	def _setCaretOffset(self, offset):
		self._selectionObject.MoveToAbsoluteOffset(offset + 1)

	def _setSelectionOffsets(self, start, end):
		self._selectionObject.MoveToAbsoluteOffset(start + 1)
		self._selectionObject.MoveToAbsoluteOffset(end + 1, True)

	def _getSelectionOffsets(self):
		startPos = self._selectionObject.ActivePoint.CreateEditPoint().AbsoluteCharOffset - 1
		endPos = self._selectionObject.AnchorPoint.CreateEditPoint().AbsoluteCharOffset -1
		return (min(startPos, endPos), max(startPos, endPos))

	def _getTextRange(self, start, end):
		editPointStart = self._createEditPoint()
		editPointStart.MoveToAbsoluteOffset(start + 1)
		return editPointStart.GetText(end - start)

	def _getWordOffsets(self, offset):
		editPointEnd = self._createEditPoint()
		editPointEnd.MoveToAbsoluteOffset(offset + 1)
		editPointEnd.WordRight()
		editPointStart = editPointEnd.CreateEditPoint()
		editPointStart.WordLeft()
		return (editPointStart.AbsoluteCharOffset -1, editPointEnd.AbsoluteCharOffset -1)

	def _getLineOffsets(self, offset):
		editPointStart = self._createEditPoint()
		editPointStart.MoveToAbsoluteOffset(offset + 1)
		editPointStart.StartOfLine()
		editPointEnd = editPointStart.CreateEditPoint()
		editPointEnd.EndOfLine()
		# Offsets are one based and exclusive
		return (editPointStart.AbsoluteCharOffset -1, editPointEnd.AbsoluteCharOffset)

	def _getLineNumFromOffset(self, offset):
		editPoint = self._createEditPoint()
		editPoint.MoveToAbsoluteOffset(offset + 1)
		return editPoint.Line

	def _getStoryLength(self):
		editPoint = self._createEditPoint()
		editPoint.EndOfDocument()
		return editPoint.AbsoluteCharOffset - 1


class VsTextEditPane(EditableText, Window):

	def _get_TextInfo(self):
		if getattr(self, "_window", None):
			return VsTextEditPaneTextInfo
		log.debugWarning("Couldn't retrieve Visual Studio window object", exc_info=True)
		return super().TextInfo

	def initOverlayClass(self):
		self._window = self.appModule.DTE.ActiveWindow
		self.location = RectLTWH(
			self._window.Left,
			self._window.Top,
			self._window.Width,
			self._window.Height
		)

	def event_valueChange(self):
		pass


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
